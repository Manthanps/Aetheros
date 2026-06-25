"""
Webhook Handlers — Business Logic
===================================
Each handler processes one type of webhook event.

product.created / product.updated flow (7 steps):
    1. Save / update product in PostgreSQL
    2. Update RAG vector database
    3. Call run_creator_agent() — picks strategy and prepares creative package
    4. Optionally call Content Agent for final copy
    5. Package Canva/Meta assets and save a CampaignDraft (status = "draft")
    6. Return a detailed result with the draft ID

All drafts must be approved by a human before they are published.
No real Canva or Meta API calls are made here.
"""
from __future__ import annotations
import logging
import os
from datetime import datetime
from typing import Any
from webhooks.event_schemas import InventoryData, OrderData, ProductData, WebhookResult
from mcp_server.env_loader import load_environment
load_environment()
logger = logging.getLogger(__name__)

def _upsert_product(product: ProductData) -> dict[str, Any]:
    """Save a new product or update an existing one in the products table."""
    try:
        from sqlalchemy import create_engine, text as sql_text
        engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://mynat:password@localhost:5432/mynat_ai'))
        with engine.connect() as conn:
            conn.execute(sql_text('\n                INSERT INTO products\n                    (id, product_name, description, price, category,\n                     image_url, is_active, scraped_at, updated_at)\n                VALUES\n                    (:id, :name, :desc, :price, :category,\n                     :image_url, :active, now(), now())\n                ON CONFLICT (id) DO UPDATE SET\n                    product_name = EXCLUDED.product_name,\n                    description  = EXCLUDED.description,\n                    price        = EXCLUDED.price,\n                    category     = EXCLUDED.category,\n                    image_url    = EXCLUDED.image_url,\n                    is_active    = EXCLUDED.is_active,\n                    updated_at   = now()\n            '), {'id': product.id, 'name': product.name, 'desc': product.description, 'price': str(product.price), 'category': product.category, 'image_url': product.image_url, 'active': product.is_active})
            conn.commit()
        return {'ok': True, 'product_id': product.id}
    except Exception as e:
        logger.error(f'DB upsert failed for product {product.id}: {e}')
        return {'ok': False, 'error': str(e)}

def _soft_delete_product(product_id: str) -> dict[str, Any]:
    """Mark a product as inactive (is_active = false). Preserves analytics history."""
    try:
        from sqlalchemy import create_engine, text as sql_text
        engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://mynat:password@localhost:5432/mynat_ai'))
        with engine.connect() as conn:
            conn.execute(sql_text('\n                UPDATE products SET is_active = false, updated_at = now() WHERE id = :id\n            '), {'id': product_id})
            conn.commit()
        return {'ok': True}
    except Exception as e:
        logger.error(f'DB soft-delete failed for {product_id}: {e}')
        return {'ok': False, 'error': str(e)}

def _update_stock(product_id: str, new_stock: int) -> dict[str, Any]:
    """Touch updated_at when stock changes."""
    try:
        from sqlalchemy import create_engine, text as sql_text
        engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://mynat:password@localhost:5432/mynat_ai'))
        with engine.connect() as conn:
            conn.execute(sql_text('\n                UPDATE products SET updated_at = now() WHERE id = :id\n            '), {'id': product_id})
            conn.commit()
        return {'ok': True}
    except Exception as e:
        return {'ok': False, 'error': str(e)}

def _refresh_rag(product: ProductData) -> dict[str, Any]:
    """Ingest (or re-ingest) the product into ChromaDB for semantic search."""
    try:
        from mcp_server.tools.product_rag_tool import ingest_products_to_rag
        return ingest_products_to_rag([{'name': product.name, 'description': product.description, 'price': str(product.price), 'category': product.category, 'image_url': product.image_url, 'product_url': product.product_url}])
    except Exception as e:
        logger.error(f'RAG refresh failed for product {product.id}: {e}')
        return {'success': False, 'error': str(e)}
CONTENT_TRIGGER_FIELDS: frozenset[str] = frozenset({'description', 'image_url', 'category'})

def _get_review_data(product_id: str) -> dict[str, Any]:
    """Fetch the latest review sentiment for a product from the DB."""
    try:
        from sqlalchemy import create_engine, text as sql_text
        engine = create_engine(os.getenv('DATABASE_URL', 'postgresql://mynat:password@localhost:5432/mynat_ai'))
        with engine.connect() as conn:
            row = conn.execute(sql_text("\n                SELECT\n                    AVG(rating)                                          AS avg_rating,\n                    COUNT(*) FILTER (WHERE sentiment = 'positive')      AS pos,\n                    COUNT(*) FILTER (WHERE sentiment = 'negative')      AS neg,\n                    COUNT(*)                                             AS total\n                FROM reviews\n                WHERE product_id = :pid\n                  AND created_at >= now() - interval '90 days'\n            "), {'pid': product_id}).fetchone()
        if row and row.total:
            positive_pct = int(row.pos / row.total * 100)
            overall = 'very_positive' if positive_pct >= 70 else 'positive' if positive_pct >= 50 else 'mixed' if positive_pct >= 30 else 'negative'
            return {'overall_sentiment': overall, 'star_rating': round(float(row.avg_rating or 4.0), 1), 'marketing_strengths': ['natural ingredients', 'Ayurvedic formula'], 'avoid_mentioning': []}
    except Exception as e:
        logger.debug(f'  → Could not fetch review data for {product_id}: {e}')
    return {}

def _run_creator_and_save_draft(product: ProductData, trigger_event: str, run_content_agent: bool=True, changed_fields: list[str] | None=None) -> dict[str, Any]:
    """
    Run Creator Agent (and optionally Content Agent) for a product,
    then save the combined result as a CampaignDraft.

    Steps:
        1. Build product dict
        2. Call run_creator_agent() — strategy: seasonal angle, audience, platform
        3. Optionally call run_content_agent() — execution: all 10 content formats
        4. Save combined output as CampaignDraft (status = "draft")

    Args:
        product:           Product data from the webhook
        trigger_event:     Event label for the DB record
        run_content_agent: If True, run Content Agent after Creator Agent
        changed_fields:    Fields that changed (for product.updated); controls
                           whether Content Agent runs for minor updates

    Returns:
        Dict with at least: success (bool), draft_id (int|None), message (str)
    """
    product_dict = {'id': product.id, 'name': product.name, 'description': product.description, 'price': product.price, 'stock': product.stock, 'category': product.category, 'image_url': product.image_url, 'product_url': product.product_url, 'tags': product.tags}
    try:
        from agents.campaign_creator import run_creator_agent as _run_creator
        logger.info(f"  → Running Creator Agent for '{product.name}'...")
        creator_result = _run_creator(products=[product_dict], month=datetime.now().month)
    except Exception as e:
        logger.error(f"  ✗ Creator Agent failed for '{product.name}': {e}")
        return {'success': False, 'draft_id': None, 'error': f'Creator Agent error: {e}'}
    if not creator_result.get('success'):
        err = creator_result.get('error', 'Unknown creator agent error')
        logger.warning(f'  ✗ Creator Agent returned failure: {err}')
        return {'success': False, 'draft_id': None, 'error': err}
    logger.info(f"  ✓ Creator Agent done — recommended: '{creator_result.get('recommended_product')}', platform: {creator_result.get('platform')}")
    content_result: dict[str, Any] = {}
    needs_content = run_content_agent and (changed_fields is None or bool(CONTENT_TRIGGER_FIELDS & set(changed_fields)))
    if needs_content:
        try:
            from agents.caption_writer import run_content_agent as _run_content
            logger.info(f"  → Running Content Agent for '{product.name}'...")
            public_response = _get_review_data(product.id)
            content_result = _run_content(product_data=product_dict, creator_output=creator_result, public_response=public_response or None, month=datetime.now().month)
            if content_result.get('success'):
                try:
                    from agents.campaign_creator import CreatorAssetRequest
                    from agents.campaign_creator import CreatorAssetService
                    package_request = CreatorAssetRequest(product_data=product_dict, content_output=content_result, creator_strategy=creator_result, platform=creator_result.get('platform', 'instagram'), asset_type=creator_result.get('content_type', 'post') if creator_result.get('content_type') in {'story', 'carousel'} else 'social_post', workflow_id=creator_result.get('workflow_id', 'untracked'))
                    creative_package = CreatorAssetService().generate_package(package_request).model_dump(mode='json')
                    creator_result['creative_package'] = creative_package
                    creator_result['canva_design_prompt'] = (creative_package.get('canva') or {}).get('design_prompt', '')
                    creator_result['meta_payload'] = (creative_package.get('meta') or {}).get('meta_payload', {})
                    creator_result['instagram_payload'] = (creative_package.get('meta') or {}).get('instagram_payload', {})
                    creator_result['facebook_payload'] = (creative_package.get('meta') or {}).get('facebook_payload', {})
                except Exception as package_error:
                    logger.warning(f'  ✗ Creator packaging failed — continuing with content: {package_error}')
                logger.info(f"  ✓ Content Agent done — brand_safe={content_result.get('_brand_safety', {}).get('brand_safe')}, fallback={content_result.get('_meta', {}).get('fallback_used')}")
            else:
                logger.warning(f'  ✗ Content Agent returned failure — continuing with Creator output only')
                content_result = {}
        except Exception as e:
            logger.error(f"  ✗ Content Agent error for '{product.name}': {e} — continuing without it")
            content_result = {}
    else:
        logger.info(f"  → Content Agent skipped ({('minor field change' if changed_fields else 'not requested')})")
    try:
        if content_result.get('success'):
            from backend.database.campaign_store import save_content_draft
            save_result = save_content_draft(product_id=product.id, product_name=product.name, trigger_event=trigger_event, content_result=content_result, creator_result=creator_result)
        else:
            from backend.database.campaign_store import save_campaign_draft
            save_result = save_campaign_draft(product_id=product.id, product_name=product.name, trigger_event=trigger_event, creator_result=creator_result)
    except Exception as e:
        logger.error(f'  ✗ Draft save failed: {e}')
        return {'success': True, 'draft_id': None, 'warning': f'Content generated but draft not saved: {e}', 'recommended_product': creator_result.get('recommended_product'), 'platform': creator_result.get('platform')}
    draft_id = save_result.get('draft_id')
    if save_result.get('ok'):
        logger.info(f'  ✓ Campaign draft saved — id={draft_id}')
    else:
        logger.warning(f"  ✗ Draft save error: {save_result.get('error')}")
    return {'success': True, 'draft_id': draft_id, 'recommended_product': creator_result.get('recommended_product'), 'platform': creator_result.get('platform'), 'content_type': creator_result.get('content_type'), 'content_agent_ran': bool(content_result.get('success')), 'message': f"Draft #{draft_id} created for '{creator_result.get('recommended_product')}'" + (' with full content' if content_result.get('success') else '')}

def handle_product_created(product: ProductData) -> WebhookResult:
    """
    Process 'product.created' event.

    A new product appeared on mynat.in — save it, index it for RAG,
    run the Creator Agent, and save the campaign strategy as a draft.
    """
    logger.info(f"[HANDLER] product.created  id={product.id}  name='{product.name}'")
    steps: list[str] = []
    errors: list[str] = []
    content: dict = {}
    db = _upsert_product(product)
    if db['ok']:
        steps.append('database_saved')
        logger.info('  ✓ Saved to PostgreSQL')
    else:
        errors.append(f"DB error: {db['error']}")
        logger.warning(f"  ✗ DB save failed: {db['error']}")
    rag = _refresh_rag(product)
    if rag.get('success'):
        steps.append('rag_updated')
        logger.info('  ✓ Added to ChromaDB RAG')
    else:
        errors.append(f"RAG error: {rag.get('error')}")
        logger.warning(f"  ✗ RAG update failed: {rag.get('error')}")
    creator = _run_creator_and_save_draft(product, trigger_event='product.created', run_content_agent=True, changed_fields=None)
    if creator['success']:
        steps.append('creator_agent_ran')
        if creator.get('draft_id'):
            steps.append('campaign_draft_saved')
        content = creator
        logger.info(f"  ✓ {creator.get('message', 'Creator Agent done')}")
    else:
        errors.append(f"Creator Agent: {creator.get('error')}")
    return WebhookResult(success=len(steps) > 0, event='product.created', message=f"New product '{product.name}' processed — draft #{creator.get('draft_id', '?')} created", steps_completed=steps, content_generated=content, errors=errors)

def handle_product_updated(product: ProductData, changed_fields: list[str]) -> WebhookResult:
    """
    Process 'product.updated' event.

    Updates DB + RAG. Only regenerates content when marketing-relevant
    fields changed (name, price, description, image_url, category).
    Skips Creator Agent for minor changes like tag edits.
    """
    logger.info(f"[HANDLER] product.updated  id={product.id}  name='{product.name}'  changed={changed_fields or '?'}")
    steps: list[str] = []
    errors: list[str] = []
    content: dict = {}
    db = _upsert_product(product)
    if db['ok']:
        steps.append('database_updated')
    else:
        errors.append(f"DB error: {db['error']}")
    rag = _refresh_rag(product)
    if rag.get('success'):
        steps.append('rag_refreshed')
    else:
        errors.append(f"RAG error: {rag.get('error')}")
    marketing_fields = {'price', 'description', 'image_url', 'name', 'category'}
    needs_new_content = not changed_fields or bool(marketing_fields & set(changed_fields))
    if needs_new_content:
        trigger_label = 'product.updated:' + (','.join(changed_fields) if changed_fields else 'unknown')
        creator = _run_creator_and_save_draft(product, trigger_event=trigger_label, run_content_agent=True, changed_fields=changed_fields)
        if creator['success']:
            steps.append('creator_agent_ran')
            if creator.get('draft_id'):
                steps.append('campaign_draft_saved')
            content = creator
        else:
            errors.append(f"Creator Agent: {creator.get('error')}")
    else:
        steps.append('creator_agent_skipped_minor_change')
        logger.info(f'  → Skipped Creator Agent (changed fields: {changed_fields})')
    return WebhookResult(success=len(steps) > 0, event='product.updated', message=f"Product '{product.name}' updated" + (f" — draft #{content.get('draft_id')} created" if content.get('draft_id') else ''), steps_completed=steps, content_generated=content, errors=errors)

def handle_product_deleted(product_id: str, product_name: str='') -> WebhookResult:
    """
    Process 'product.deleted' event.
    Soft-deletes the product — marks inactive, preserves analytics and RAG history.
    """
    logger.info(f"[HANDLER] product.deleted  id={product_id}  name='{product_name}'")
    db = _soft_delete_product(product_id)
    steps = ['database_soft_deleted'] if db['ok'] else []
    errors = [db.get('error', '')] if not db['ok'] else []
    steps.append('rag_preserved_for_history')
    return WebhookResult(success=True, event='product.deleted', message=f"Product '{product_name or product_id}' deactivated (soft delete)", steps_completed=steps, errors=errors)

def handle_order_created(order: OrderData) -> WebhookResult:
    """
    Process 'order.created' event.
    Logs the order and queues a WhatsApp confirmation (mock until real API connected).
    """
    logger.info(f'[HANDLER] order.created  id={order.id}  customer={order.customer_name}')
    confirmation_msg = f"Hi {order.customer_name}! 🌿 Your Mynat order #{order.id} for ₹{order.total_amount:.0f} has been confirmed. We'll update you when it ships. Thank you!"
    content = {'whatsapp_confirmation': {'mock': True, 'to': order.customer_phone or order.customer_email, 'message': confirmation_msg, 'note': 'Replace mock with real send_whatsapp_message() to actually send'}}
    return WebhookResult(success=True, event='order.created', message=f'Order #{order.id} from {order.customer_name} acknowledged', steps_completed=['order_received', 'whatsapp_confirmation_queued'], content_generated=content, errors=[])

def handle_inventory_updated(inventory: InventoryData) -> WebhookResult:
    """
    Process 'inventory.updated' event.

    Behaviour by stock level:
    - stock == 0      → out-of-stock alert (mock: pause ads, notify admin)
    - stock < 10      → generate urgency caption ("Only X left!")
    - was 0, now > 0  → back-in-stock alert (mock: send campaign to waitlist)
    """
    logger.info(f'[HANDLER] inventory.updated  id={inventory.product_id}  stock: {inventory.old_stock} → {inventory.new_stock}')
    steps: list[str] = []
    errors: list[str] = []
    content: dict = {}
    name = inventory.product_name or f'Product {inventory.product_id}'
    db = _update_stock(inventory.product_id, inventory.new_stock)
    if db['ok']:
        steps.append('database_stock_updated')
    else:
        errors.append(f"DB error: {db.get('error')}")
    if inventory.new_stock == 0:
        steps.append('out_of_stock_detected')
        content['alert'] = {'type': 'out_of_stock', 'product': name, 'action_required': 'Pause Meta ads and notify admin', 'mock': True}
        logger.warning(f'  ⚠ OUT OF STOCK: {name}')
    elif inventory.new_stock < 10:
        steps.append('low_stock_detected')
        try:
            from mcp_server.tools.content_gen_tool import generate_caption
            urgency = generate_caption(product_name=name, product_description=f'Limited — only {inventory.new_stock} units left!', tone='enthusiastic', include_cta=True)
            content['urgency_caption'] = urgency
            steps.append('urgency_content_generated')
            logger.info(f'  ✓ Urgency caption generated ({inventory.new_stock} units left)')
        except Exception as e:
            errors.append(f'Urgency content error: {e}')
    elif inventory.old_stock == 0 and inventory.new_stock > 0:
        steps.append('back_in_stock_detected')
        content['back_in_stock_alert'] = {'type': 'back_in_stock', 'product': name, 'new_stock': inventory.new_stock, 'action': 'Send back-in-stock campaign to waitlist', 'mock': True}
        logger.info(f'  ✓ Back in stock: {name} ({inventory.new_stock} units)')
    return WebhookResult(success=True, event='inventory.updated', message=f"Inventory update processed for '{name}'", steps_completed=steps, content_generated=content, errors=errors)

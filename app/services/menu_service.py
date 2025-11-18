from datetime import date
from typing import Dict, List, Optional

from sqlalchemy.orm import Session, selectinload

from app.models.menu import MenuItem, OptionGroup, OptionItem
from app.schemas.menu import MenuItemCreate, MenuItemUpdate, OptionGroupCreate


MAX_PAGE_SIZE = 50
# NFR-BE-4 Scalability: simple per-process cache – replace with Redis/central cache when scaling horizontally.
_menu_cache: Dict[str, Optional[object]] = {"date": None, "item_ids": None}


class MenuItemNotFoundError(Exception):
    """Raised when the requested menu item does not exist."""


class InvalidSeasonWindowError(Exception):
    """Raised when a seasonal item has an invalid date window."""


def _invalidate_menu_cache() -> None:
    _menu_cache["date"] = None
    _menu_cache["item_ids"] = None


def _is_in_season(item: MenuItem, today: date) -> bool:
    if not item.is_seasonal:
        return True
    if not item.season_start or not item.season_end:
        return False
    return item.season_start <= today <= item.season_end


def validate_season_window(
    is_seasonal: bool,
    season_start: Optional[date],
    season_end: Optional[date],
) -> None:
    if not is_seasonal:
        return
    if not season_start or not season_end:
        raise InvalidSeasonWindowError(
            "Seasonal items must have both season_start and season_end."
        )
    if season_start > season_end:
        raise InvalidSeasonWindowError("season_start must be before or equal to season_end.")


def _create_option_group(
    db: Session,
    item: MenuItem,
    group_in: OptionGroupCreate,
) -> None:
    group = OptionGroup(
        menu_item_id=item.id,
        name=group_in.name,
        is_required=group_in.is_required,
        min_select=group_in.min_select,
        max_select=group_in.max_select,
    )
    db.add(group)
    db.flush()

    for option_in in group_in.options:
        option = OptionItem(
            group_id=group.id,
            name=option_in.name,
            price_delta=option_in.price_delta,
            is_default=option_in.is_default,
        )
        db.add(option)


def create_menu_item(db: Session, item_in: MenuItemCreate) -> MenuItem:
    validate_season_window(item_in.is_seasonal, item_in.season_start, item_in.season_end)

    item = MenuItem(
        name=item_in.name,
        description=item_in.description,
        price=item_in.price,
        category=item_in.category,
        tags=item_in.tags,
        is_seasonal=item_in.is_seasonal,
        season_start=item_in.season_start,
        season_end=item_in.season_end,
        is_available=item_in.is_available,
        stock_quantity=item_in.stock_quantity,
    )
    db.add(item)
    db.flush()

    for group_in in item_in.option_groups:
        _create_option_group(db, item, group_in)

    db.commit()
    db.refresh(item)
    _invalidate_menu_cache()
    return item


def get_menu_item_or_404(db: Session, item_id: int) -> MenuItem:
    item = db.query(MenuItem).filter(MenuItem.id == item_id).first()
    if not item:
        raise MenuItemNotFoundError(f"Menu item {item_id} not found")
    return item


def update_menu_item(db: Session, item_id: int, item_in: MenuItemUpdate) -> MenuItem:
    item = get_menu_item_or_404(db, item_id)
    data = item_in.dict(exclude_unset=True)

    if "name" in data:
        item.name = data["name"]
    if "description" in data:
        item.description = data["description"]
    if "price" in data:
        item.price = data["price"]
    if "category" in data:
        item.category = data["category"]
    if "tags" in data:
        item.tags = data["tags"]
    if "is_seasonal" in data:
        item.is_seasonal = data["is_seasonal"]
    if "season_start" in data:
        item.season_start = data["season_start"]
    if "season_end" in data:
        item.season_end = data["season_end"]
    if "is_available" in data:
        item.is_available = data["is_available"]
    if "stock_quantity" in data:
        item.stock_quantity = data["stock_quantity"]

    validate_season_window(item.is_seasonal, item.season_start, item.season_end)

    if "option_groups" in data:
        for group in list(item.option_groups):
            db.delete(group)
        db.flush()
        for group_in in data["option_groups"]:
            _create_option_group(db, item, group_in)

    db.add(item)
    db.commit()
    db.refresh(item)
    _invalidate_menu_cache()
    return item


def delete_menu_item(db: Session, item_id: int) -> None:
    item = get_menu_item_or_404(db, item_id)
    db.delete(item)
    db.commit()
    _invalidate_menu_cache()


def list_all_menu_items(db: Session, limit: int = 20, offset: int = 0) -> List[MenuItem]:
    """Return menu items for admin views with pagination (# NFR-BE-1 Performance)."""

    normalized_limit = max(1, min(limit, MAX_PAGE_SIZE))
    query = (
        db.query(MenuItem)
        .options(selectinload(MenuItem.option_groups).selectinload(OptionGroup.options))
        .order_by(MenuItem.created_at.desc())
        .offset(max(0, offset))
        .limit(normalized_limit)
    )
    return query.all()


def _cache_hit(today: date) -> Optional[List[int]]:
    if _menu_cache["date"] == today and _menu_cache["item_ids"] is not None:
        return _menu_cache["item_ids"]
    return None


def list_visible_menu_items(
    db: Session,
    limit: Optional[int] = None,
    offset: int = 0,
) -> List[MenuItem]:
    today = date.today()
    cached_ids = _cache_hit(today)
    if cached_ids is not None:
        if not cached_ids:
            return []
        query = (
            db.query(MenuItem)
            .options(selectinload(MenuItem.option_groups).selectinload(OptionGroup.options))
            .filter(MenuItem.id.in_(cached_ids))
        )
        items_by_id = {item.id: item for item in query.all()}
        ordered_items = [items_by_id[item_id] for item_id in cached_ids if item_id in items_by_id]
        if limit is None:
            return ordered_items
        normalized_limit = max(1, min(limit, MAX_PAGE_SIZE))
        start = max(0, offset)
        end = start + normalized_limit
        return ordered_items[start:end]

    available_items = (
        db.query(MenuItem)
        .options(selectinload(MenuItem.option_groups).selectinload(OptionGroup.options))
        .filter(MenuItem.is_available == True)
        .order_by(MenuItem.created_at.desc())
        .all()
    )
    visible = [item for item in available_items if _is_in_season(item, today)]
    _menu_cache["date"] = today
    _menu_cache["item_ids"] = [item.id for item in visible]
    # TODO: replace this in-memory cache with Redis or shared cache when scaling.
    if limit is None:
        return visible
    normalized_limit = max(1, min(limit, MAX_PAGE_SIZE))
    start = max(0, offset)
    end = start + normalized_limit
    return visible[start:end]

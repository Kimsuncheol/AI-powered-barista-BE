from sqlalchemy.orm import Session

from app.models.preference import Preference
from app.schemas.preference import PreferencesOut


def get_preferences_for_user(db: Session, user_id: int) -> PreferencesOut:
    preference = db.query(Preference).filter(Preference.user_id == user_id).first()
    if not preference:
        preference = Preference(user_id=user_id)
        db.add(preference)
        db.commit()
        db.refresh(preference)

    return PreferencesOut(
        favorite_drinks=preference.favorite_drinks or [],
        default_size=preference.default_size,
        default_milk_type=preference.default_milk_type,
        default_sugar_level=preference.default_sugar_level,
    )

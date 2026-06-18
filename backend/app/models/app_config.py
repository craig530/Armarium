from sqlalchemy import Column, Integer, String, Text
from ..database import Base


class AppConfig(Base):
    """Singleton configuration table (always exactly one row, id=1).

    ownership_mode:
      'shared'   — all items default to the hidden "shared" system user.
      'by_login' — every item/list defaults to the creating user's login.

    disabled_categories:
      JSON array of MediaCategory values that are hidden from the UI,
      e.g. '["books", "music"]'. Default '[]' means all categories visible.
    """

    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True)
    ownership_mode = Column(String(20), nullable=False, default="shared", server_default="shared")
    disabled_categories = Column(Text, nullable=False, default="[]", server_default="'[]'")

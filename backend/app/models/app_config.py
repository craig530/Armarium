from sqlalchemy import Column, Integer, String
from ..database import Base


class AppConfig(Base):
    """Singleton configuration table (always exactly one row, id=1).

    ownership_mode:
      'shared'   — all items default to the hidden "shared" system user;
                   the owner field is optional and informational.
      'by_login' — every item/list defaults to the creating user's login;
                   the shared pseudo-user is never used for new content.
    """

    __tablename__ = "app_config"

    id = Column(Integer, primary_key=True)
    ownership_mode = Column(String(20), nullable=False, default="shared", server_default="shared")

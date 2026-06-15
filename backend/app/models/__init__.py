from .enums import LinkMatchType, MediaCategory, Supertype
from .item_link import ItemLink
from .item_list import ItemList
from .location import Location
from .media import MediaItem
from .media_subtype import MediaSubtype
from .platform import Platform
from .plex_config import PlexConfig
from .plex_library_mapping import PlexLibraryMapping
from .user import User

# Re-exported so importing this module registers every ORM class on
# Base.metadata (required by Alembic autogenerate and Base.metadata.create_all
# for in-memory test DBs), even though nothing here references them directly.
__all__ = [
    "LinkMatchType",
    "MediaCategory",
    "Supertype",
    "ItemLink",
    "ItemList",
    "Location",
    "MediaItem",
    "MediaSubtype",
    "Platform",
    "PlexConfig",
    "PlexLibraryMapping",
    "User",
]

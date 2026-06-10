import enum


class Supertype(str, enum.Enum):
    PHYSICAL = "physical"
    DIGITAL = "digital"


class MediaCategory(str, enum.Enum):
    MUSIC = "music"
    FILMS_TV = "films_tv"
    BOOKS = "books"

from pydantic import BaseModel

from pantheon.smart_func import smart_func
from _llm_guard import requires_llm


@requires_llm
async def test_smart_func():
    @smart_func
    async def translate(text: str) -> str:
        """Translate the given text to English."""

    res = await translate("你好，世界！")
    assert res.lower() == "hello, world!"


@requires_llm
async def test_smart_func_with_tools():
    _city = None

    def get_weather(city: str):
        nonlocal _city
        _city = city
        return {"weather": "sunny"}

    @smart_func(tools=[get_weather])
    async def get_weather_info(city: str) -> str:
        """Get the weather information of the given city."""

    await get_weather_info("Palo Alto")
    assert _city.lower() == "palo alto"


@requires_llm
async def test_smart_func_structured_output():
    class Book(BaseModel):
        title: str
        author: str
        price: float

    @smart_func
    async def recommend_book() -> Book:
        """Recommend a book."""

    book = await recommend_book()
    assert isinstance(book, Book)


@requires_llm
def test_smart_func_sync():
    @smart_func
    def translate(text: str) -> str:
        """Translate the given text to English."""

    res = translate("你好，世界！")
    assert res.lower() == "hello, world!"

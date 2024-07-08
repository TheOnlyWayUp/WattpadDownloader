from .. import create_book


import pytest

STORY_ID = 372219540


@pytest.mark.asyncio
async def test_retrieve_story():
    story_data = await create_book.retrieve_story(STORY_ID)
    story_data.pop("modifyDate", None)  # Subject to change

    response = {
        "id": "372219540",
        "title": "WPD Test",
        "createDate": "2024-07-02T15:29:13Z",
        # "modifyDate": "2024-07-02T15:41:26Z",
        "language": {"name": "English"},
        "user": {"username": "KindaAssNgl"},
        "description": "Testing story for WPD.",
        "cover": r"https:\/\/img.wattpad.com\/cover\/372219540-256-k908955.jpg",
        "completed": False,
        "tags": ["testing", "towu", "wpd"],
        "mature": False,
        "url": r"https:\/\/www.wattpad.com\/story\/372219540-wpd-test",
        "parts": [{"id": 1458516761, "title": "Ganesh"}],
        "isPaywalled": False,
    }

    assert story_data == response

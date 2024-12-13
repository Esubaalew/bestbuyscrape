from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.docs import get_redoc_html, get_swagger_ui_html
from fastapi.responses import RedirectResponse
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

app = FastAPI(
    title="Best Buy Scraper API",
    description="API for extracting product and category data from Best Buy's website. "
                "Explore product details, categories, and more with ease.",
    summary="Best Buy Scraper: Your gateway to live product data from Best Buy.",
    contact={
        "name": "Esubalew Chekol",
        "url": "https://github.com/esubaalew",
        "email": "esubaalew@example.com",
    },
    version="1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

BASE_URL = "https://www.bestbuy.com"


async def fetch_page_source(url: str) -> str:
    """Fetch the page source using Playwright in headless mode."""
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        await page.goto(url)
        if "Choose a country" in await page.content():
            await page.click('a.us-link')
            await page.wait_for_load_state('networkidle')
        content = await page.content()
        await browser.close()
        return content


@app.get("/categories", summary="Fetch all categories", tags=["Categories"])
async def fetch_categories():
    """
    Retrieve all available product categories from Best Buy's homepage.

    Returns:
        dict: A dictionary containing the names and URLs of all categories.
    """
    try:
        page_source = await fetch_page_source(BASE_URL)
        soup = BeautifulSoup(page_source, "html.parser")
        categories = []
        for item in soup.select('li.c-carousel-item'):
            category = item.find('a')
            if category:
                name = category.get_text(strip=True)
                url = category['href']
                categories.append({'name': name, 'url': BASE_URL + url})
        return {"categories": categories}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/category-products", summary="Fetch products by category name", tags=["Products"])
async def fetch_category_products(
    category_name: str = Query(..., description="The name of the category to fetch products from.")
):
    """
    Retrieve product details for a specific category by its name.

    Args:
        category_name (str): The name of the category to retrieve products for.

    Returns:
        dict: A dictionary containing product details (name, image, price).
    """
    try:
        # Fetch all categories to find the matching category
        page_source = await fetch_page_source(BASE_URL)
        soup = BeautifulSoup(page_source, "html.parser")
        categories = []
        for item in soup.select('li.c-carousel-item'):
            category = item.find('a')
            if category:
                name = category.get_text(strip=True)
                url = category['href']
                categories.append({'name': name, 'url': BASE_URL + url})

        # Find the category URL matching the provided name
        category = next((cat for cat in categories if cat['name'].lower() == category_name.lower()), None)
        if not category:
            raise HTTPException(status_code=404, detail=f"Category '{category_name}' not found.")

        # Fetch products from the matched category
        page_source = await fetch_page_source(category['url'])
        soup = BeautifulSoup(page_source, "html.parser")
        products = []
        for item in soup.select('li.sku-item'):
            name_tag = item.select_one('h4.sku-title a')
            image_tag = item.select_one('img.product-image')
            price_tag = item.select_one('div.priceView-hero-price span')
            if name_tag and image_tag and price_tag:
                products.append({
                    'name': name_tag.text.strip(),
                    'photo': image_tag['src'],
                    'price': price_tag.text.strip()
                })
        return {"products": products}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/", include_in_schema=False)
async def root():
    """
    Redirect to API documentation.
    """
    return RedirectResponse(url="/docs")


@app.get("/docs", include_in_schema=False)
async def custom_swagger_ui_html():
    """
    Redirect to Swagger UI.
    """
    return get_swagger_ui_html(openapi_url="/openapi.json", title="Best Buy Scraper API")


@app.get("/redoc", include_in_schema=False)
async def redoc_html():
    """
    Redirect to Redoc UI.
    """
    return get_redoc_html(openapi_url="/openapi.json", title="Best Buy Scraper API")

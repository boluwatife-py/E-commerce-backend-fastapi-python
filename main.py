from fastapi import FastAPI
from app.exceptions import validation_exception_handler
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse


app = FastAPI(title="E-Commerce API")

app.add_exception_handler(RequestValidationError, validation_exception_handler)

app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/offline-docs/", include_in_schema=False)
def get_offline_docs():
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>API Documentation</title>
        <link rel="stylesheet" type="text/css" href="/static/swagger-ui/swagger-ui.css">
        <script src="/static/swagger-ui/swagger-ui-bundle.js"></script>
        <script src="/static/swagger-ui/swagger-ui-standalone-preset.js"></script>
    </head>
    <body>
        <div id="swagger-ui"></div>
        <script>
            const ui = SwaggerUIBundle({
                url: '/openapi.json',  // Uses local OpenAPI schema
                dom_id: '#swagger-ui',
                presets: [SwaggerUIBundle.presets.apis, SwaggerUIStandalonePreset],
                layout: "StandaloneLayout"
            });
        </script>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)




ALLOWED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
    
)
@app.get("/", tags=['Root'])
def root():
    return {"message": "E-Commerce API is running"}



from app.routes import (auth, misc, products, user, admins, cart)

from fastapi.exceptions import RequestValidationError


app.include_router(auth.router, prefix="/auth", include_in_schema=True) #  AUTH ROUTE
app.include_router(user.router, prefix="/user", include_in_schema=True) #  USERS ROUTE
app.include_router(admins.router, prefix="/admin", include_in_schema=False) #  ADMIN ROUTE
app.include_router(products.router, prefix="/products", include_in_schema=True) #  PRODUCTS ROUTE
app.include_router(cart.router, prefix="/cart", include_in_schema=True) #  CART ROUTE
app.include_router(misc.router, prefix="/misc", include_in_schema=True) #  MISC ROUTE


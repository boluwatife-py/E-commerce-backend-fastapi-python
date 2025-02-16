from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from core.database import get_db
from app.models import Product, User, Category, ProductImages, Currency
from app.schemas import ProductResponse, ProductCreate, cpr, CategoryResponse, CurrencyResponse, ProductImageResponse, ImageRankUpdatePayload
from core.auth import require_role
from typing import Annotated, Optional, List
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload


router = APIRouter()


from sqlalchemy import select
from sqlalchemy.orm import selectinload
from typing import Optional, List
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession


@router.get("/", response_model=List[ProductResponse])
async def get_products(
    db: AsyncSession = Depends(get_db),
    category_name: Optional[str] = None,
    brand: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    limit: int = 10,
    offset: int = 0
):
    try:
        if limit <= 0 or limit > 100:
            raise HTTPException(status_code=400, detail="Limit must be between 1 and 100")
        if offset < 0:
            raise HTTPException(status_code=400, detail="Offset must be 0 or greater")

        query = (
            select(Product)
            .options(
                selectinload(Product.product_images),
                selectinload(Product.currency),
                selectinload(Product.category)
            )
            .filter(Product.status == 'published', Product.stock_quantity > 0)
        )

        if category_name:
            query = query.join(Product.category).filter(Product.category.has(name=category_name))

        if brand:
            query = query.filter(Product.brand == brand)

        if min_price is not None:
            if min_price < 0:
                raise HTTPException(status_code=400, detail="Minimum price must be non-negative")
            query = query.filter(Product.price >= min_price)

        if max_price is not None:
            if max_price < 0:
                raise HTTPException(status_code=400, detail="Maximum price must be non-negative")
            query = query.filter(Product.price <= max_price)

        query = query.offset(offset).limit(limit)

        result = db.execute(query)
        products = result.scalars().all()

        if not products:
            raise HTTPException(status_code=404, detail="No products found with the given filters")

        product_responses = []
        for product in products:
            first_image_url = None
            if product.product_images:
                first_image = min(product.product_images, key=lambda img: img.rank)
                first_image_url = first_image.image_url

            
            category_response = None
            if product.category:
                category_response = CategoryResponse(
                    category_id=product.category.category_id,
                    name=product.category.name
                )

            currency_response = None
            if product.currency:
                currency_response = CurrencyResponse(
                    code=product.currency.code,
                    name=product.currency.name,
                    symbol=product.currency.symbol
                )

            product_responses.append(
                ProductResponse(
                    product_id=product.product_id,
                    name=product.name,
                    description=product.description,
                    price=float(product.price) if product.price else None,
                    stock_quantity=product.stock_quantity,
                    brand=product.brand,
                    status=product.status,
                    seller_id=product.seller_id,
                    created_at=product.created_at,
                    updated_at=product.updated_at,
                    reviews=[],
                    images=[ProductImageResponse(id=0, image_url=first_image_url, rank=0)] if first_image_url else [],
                    category=category_response,
                    currency=currency_response,
                )
            )

        return product_responses

    except HTTPException:
        raise

    except Exception as e:
        print(f"Error retrieving products: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while fetching products.")

@router.get("/{product_id}/product/view/", response_model=ProductResponse)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    try:
        result = db.execute(
            select(Product)
            .options(
                selectinload(Product.product_images),
                selectinload(Product.category),
                selectinload(Product.currency)
            )
            .filter(Product.product_id == product_id, Product.status == 'published', Product.stock_quantity > 0)
        )

        product = result.scalars().first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        return ProductResponse.from_attributes(product)

    except HTTPException:
        raise

    except SQLAlchemyError as e:
        print(f"Database error while retrieving product {product_id}: {e}")
        raise HTTPException(status_code=500, detail="Database error. Please try again later.")

    except Exception as e:
        print(f"Unexpected error while retrieving product {product_id}: {e}")
        raise HTTPException(status_code=500, detail="An unexpected error occurred. Please try again later.")

@router.get('/create/product/', response_model=cpr)
async def create_product(
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    db: AsyncSession = Depends(get_db)
)-> dict:
    try:
        new_product = Product(
            seller=current_user
        )
        
        db.add(new_product)
        db.commit()
        db.refresh(new_product)
        
        return cpr(product_id=new_product.product_id)
        
    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.get("/edit/{product_id}/product/", response_model=ProductResponse)
async def get_product_for_edit(
    product_id: int,
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    db: AsyncSession = Depends(get_db),
):
    try:
        existing_product = db.get(Product, product_id)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        if existing_product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to edit this product")

        return ProductResponse.from_attributes(existing_product)

    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred: {str(e)}")

@router.put("/edit/{product_id}/product/", response_model=ProductResponse)
async def update_product(
    product_id: int,
    product: ProductCreate,
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    db: AsyncSession = Depends(get_db),
):
    try:
        existing_product = db.get(Product, product_id)

        if not existing_product:
            raise HTTPException(status_code=404, detail="Product not found")

        if existing_product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to edit this product")

        
        if product.name is not None:
            existing_product.name = product.name
        if product.description is not None:
            existing_product.description = product.description
        if product.price is not None:
            if product.price <= 0:
                raise HTTPException(status_code=400, detail="Price must be greater than 0")
            existing_product.price = product.price
        if product.stock_quantity is not None:
            if product.stock_quantity < 0:
                raise HTTPException(status_code=400, detail="Stock quantity cannot be negative")
            existing_product.stock_quantity = product.stock_quantity
        if product.brand is not None:
            existing_product.brand = product.brand

        
        if product.category_id is not None:
            category = db.get(Category, product.category_id)
            if not category:
                raise HTTPException(status_code=404, detail="Category not found")
            existing_product.category_id = product.category_id


        if product.currency_code is not None:
            currency = db.get(Currency, product.currency_code)
            if not currency:
                raise HTTPException(status_code=404, detail=f"Currency '{product.currency_code}' not found")
            existing_product.currency_code = product.currency_code

        allowed_statuses = {'draft', 'published'}
        if product.status is not None:
            if product.status not in allowed_statuses:
                raise HTTPException(
                    status_code=400,
                    detail=f"Invalid status '{product.status}'. Allowed values: {', '.join(allowed_statuses)}",
                )
            existing_product.status = product.status

            if product.status in {'published', 'available'}:
                if not all([existing_product.name, existing_product.price, existing_product.stock_quantity]):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cannot set status to '{product.status}' with missing name, price, or stock_quantity",
                    )

        db.commit()
        db.refresh(existing_product)

        return ProductResponse.from_attributes(existing_product)

    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail=f"Database error")

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail=f"An unexpected error occurred")

@router.delete("/delete/{product_id}/product/")
async def delete_product(
    product_id: int, 
    current_user: Annotated[User, Depends(require_role(['merchant']))], 
    db: AsyncSession = Depends(get_db)
):
    """
    Allows only the product owner (seller) to delete the product.
    Ensures proper error handling.
    """
    try:
        product = db.query(Product).filter(Product.product_id == product_id).first()

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        
        if product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this product")

        db.delete(product)
        db.commit()
        return {"message": "Product deleted successfully"}

    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        db.rollback()
        print(f"Error deleting product: {e}")
        raise HTTPException(status_code=500, detail="An error occurred while deleting the product.")


@router.post("/upload/image/product/")
async def upload_product_image(
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    product_id: int = Form(...),
    image: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    try:
        product = db.get(Product, product_id)

        if not product:
            raise HTTPException(status_code=404, detail="Product not found")

        if product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to upload images for this product")

        
        result = db.execute(
            select(func.count())
            .select_from(ProductImages)
            .filter(ProductImages.product_id == product.product_id)
        )
        image_count = result.scalar()

        if image_count >= 10:
            raise HTTPException(status_code=400, detail="A product can have a maximum of 10 images")

        
        result = db.execute(
            select(func.max(ProductImages.rank))
            .filter(ProductImages.product_id == product.product_id)
        )
        max_rank = result.scalar() or 0.0
        next_rank = max_rank + 1.0

        
        image_url = f"https://example.com/uploads/{image.filename}"

        new_image = ProductImages(
            product_id=product.product_id,
            image_url=image_url,
            rank=next_rank
        )

        db.add(new_image)
        db.commit()
        db.refresh(new_image)

        return {
            "image_id": new_image.id,
            "image_url": new_image.image_url,
            "rank": new_image.rank,
            "product_id": product.product_id
        }

    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    except Exception as e:
        db.rollback()
        print(e)
        raise HTTPException(status_code=500, detail="Unexpected error occurred")


@router.put("/product-images/reorder/")
async def reorder_images(
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    product_id: int,
    payload: ImageRankUpdatePayload,
    db: AsyncSession = Depends(get_db),
):
    try:
        result = db.execute(
            select(ProductImages)
            .options(selectinload(ProductImages.product))
            .filter(ProductImages.product_id == product_id)
            .order_by(ProductImages.rank)
            .with_for_update()
        )
        images = result.scalars().all()

        if not images:
            raise HTTPException(status_code=404, detail="No images found for this product")

        product = images[0].product
        if product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to reorder images for this product")

        provided_ids = [update.id for update in payload.updates]

        db_image_ids = {image.id for image in images}
        missing_ids = [image_id for image_id in provided_ids if image_id not in db_image_ids]

        if missing_ids:
            raise HTTPException(status_code=400, detail=f"Image IDs {missing_ids} not found or do not belong to this product")

        if set(provided_ids) != db_image_ids:
            raise HTTPException(
                status_code=400,
                detail=f"All images for product {product_id} must be provided in the payload. Expected: {sorted(db_image_ids)}, Received: {sorted(provided_ids)}"
            )

        
        id_to_image = {image.id: image for image in images}
        for update in payload.updates:
            image_id = update.id
            rank = update.rank
            id_to_image[image_id].rank = float(rank)

        db.commit()

        result = db.execute(
            select(ProductImages)
            .filter(ProductImages.product_id == product_id)
            .order_by(ProductImages.rank)
        )
        updated_images = result.scalars().all()

        for img in updated_images:
            print(f"After commit - Image {img.id} -> Rank {img.rank}")

        return {"message": "Image positions updated successfully"}

    except HTTPException:
        raise

    except SQLAlchemyError as e:
        db.rollback()
        print(f"Database error: {e}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

    except Exception as e:
        db.rollback()
        print(f"Unexpected error: {e}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")


@router.delete("/product/{image_id}/images/")
async def delete_product_image(
    current_user: Annotated[User, Depends(require_role(['merchant']))],
    image_id: int,
    db: AsyncSession = Depends(get_db)):
    try:
        image = db.get(ProductImages, image_id)
        
        if not image:
            raise HTTPException(status_code=404, detail="No images found with this identifier")

        product = db.get(Product, image.product_id)
        
        if not product:
            raise HTTPException(status_code=404, detail="Product not found")
        
        if product.seller_id != current_user.user_id:
            raise HTTPException(status_code=403, detail="You do not have permission to delete this image")
        
        db.delete(image)
        db.commit()
        return {"message": "Image removed successfully"}
    
    except HTTPException as http_exc:
        raise http_exc

    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail="An error occurred while deleting image.")


# @router.post('/product/review/{product_id}/create')
# def make_review(
#     current_user: Annotated[User, Depends(require_role(['merchant']))],
#     product_id: int,
#     db: AsyncSession = Depends(get_db))
# ):
#     try:
#         product = db.get(Product).filter(Product.id == product_id).first()
        
#         if not product:
#             raise HTTPException(status_code=404, message="Product not found")
        
#         if product.seller_id == current_user.user_id:
#             raise HTTPException(status_code=403, message="You can not review your own product")
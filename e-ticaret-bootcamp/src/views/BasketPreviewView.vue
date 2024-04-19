<template>
    
    <div class="previewCard">
        <div class="previewItem">
            <div class="image">
                <img src="" />
            </div>
            <div class="content">
                <div class="title">Başlık</div>
                <div class="price">10 TL</div>
            </div>
        </div>
    </div>
    <div class="total">Toplam Fiyat : 20 TL</div>


</template>

<script>
    export default{
        name:"BasketPreview"
    }
</script>

<style scoped>
    .previewCard{
        background-color: #fff;
        border: 1px solid #d9dde0;
        border-radius: 20px;
        display: flex;
        padding: 20px;
        flex-direction: column;
    }

    .previewItem{
        display: flex;
    }

    .image{
        margin-right: 20px;
    }

    .image > img{
        width: 150px;
        height: auto;
        object-fit: fill;
    }

    .content{
        font-weight: 500;
        display: flex;
        flex-direction: column;
    }

    .price{
        margin-top: 4px;
        color: #1874ff;
        font-size: 12px;
    }

    .total{
        color: #374051;
        font-size: 32px;
        font-weight: 600;
        margin-bottom: 8px;
    }
</style>
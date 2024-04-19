<template>
    <div class="contextWrapper">
        <div class="contextItem"
        :class="{borderBottom:$store.getters.getBasketsLength-1!=i}"
        v-for="(item,i) in $store.getters.getBaskets" :key="item" >
            <div class="image">
                <img :src="item.image" />
            </div>
            <div class="content">
                <div class="title">{{ item.title }}</div>
                <div class="price">{{ item.price }}</div>
            </div>
        </div>
        <div class="contextItem complateBox" @click="goBasket">
            Sepete Git!
        </div>
    </div>
</template>

<script>
export default{
    name:"ShopContext",
    methods:{
        goBasket(){
            this.$router.push('/basket-preview')
            this.$emit('goBasket')
        }
        
    }
}
</script>
<style scoped>
    .contextWrapper{
        z-index: 10;
        background-color: #fff;
        position: absolute;
        right: 0;
        border: 1px solid #dee2e6;
        padding-top: 8px;
        padding-bottom: 8px;
        filter: drop-shadow(0px 8px 12px rgba(0,0,0,0.15));
        border-radius: 8px;
        max-width: 600px;
        min-width: 250px;
        width: max-content;
    }

    .borderBottom{
        border-bottom: 1px solid #dee2e6;
    }

    .contextItem{
        border-bottom: 1px solid #eff1f3;
        margin-bottom: 8px;
        display: flex;
        padding-left: 16px;
        padding-right: 16px;

    }

    .image{
       margin-right: 12px; 
    }

    .image > img{
        width: 50px;
        height: 50px;
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

    .title{
        font-size: 20px;
        font-weight: 600;
        color: #262B37 !important;
    }

    .complateBox{
        border-top: 1px solid #dee2e6;
        align-items: center;
        justify-content: center;
        padding-bottom: 16px;
        padding-top: 16px;
        color: #1874ff;
    }

</style>                             
<template>
    <div class="productDetailCard">
       <div class="imageSection">
            <img :src="detail.image" />
       </div>
       <div class="productInfoSection">
            <div class="title">Ürün Numarası #{{ $route.params.id }}</div>
            <div class="title">{{ detail.title }}</div>
            <div class="desc">{{ detail.description }}</div>
            <div class="price">{{ detail.price }}</div>

            <div class="rate">
                <svg 
                    v-for="item in 5" :key="item.id"
                 viewBox="0 0 24 24" width="16" height="16" 
                 :stroke="item <= Math.floor(detail.rating.rate)  ? '#1874ff' : 'currentColor' " 
                 stroke-width="2" 
                 :fill="item <= Math.floor(detail.rating.rate)  ? '#1874ff' : 'none' " 
                 stroke-linecap="round" stroke-linejoin="round" class="css-i6dzq1"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                {{ detail.rating.count }} değerlendirme
            </div>
            <div class="title">Ürün kategorisi</div>
            <div class="category">
                {{ detail.category }}
            </div>
       </div>
    </div>
</template>

<script>
    export default{
        name:"ProductDetail",
        created(){
           this.getProductById()
        },
        methods:{
            getProductById(){
                fetch('https://fakestoreapi.com/products/'+this.$route.params.id)
                .then(res=>res.json())
                .then(json=>{
                    this.detail = json
                })
            }
        },
        data(){
            return{
                detail:{
                    category:"",
                    description:"",
                    id:"",
                    image:"",
                    price:"",
                    title:"",
                    rating:{rate:0,count:0}
                }
            }
        }
    }
</script>

<style scoped>
    .productDetailCard{
        background-color: #fff;
        border: 1px solid #d9dde0;
        border-radius: 20px;
        display: flex;
        padding: 20px;

    }

    .imageSection{
        margin-right: 32px;

    }

    .productInfoSection{
        display: flex;
        flex: 1;
        flex-direction: column;
        align-items: center;

    }

    .title{
        width: 100%;
        text-align: center;
        color: #374051;
        font-size: 32px;
        font-weight: 500;
        margin-bottom: 8px;
    }

    .desc{
        color: #657282;
        font-size: 14px;
        font-weight: 400;

    }

    .price{
        margin-top: 8px;
        color: #1874ff;
        font-size: 24px;
        font-weight: 500;
    }

    .category{
        cursor: pointer;
        padding: 4px 16px;
        gap: 10px;
        background-color: #fafafa;
        border: 1px solid #d9dde0;
        text-transform: uppercase;
        font-size: 12px;
        border-radius: 16px;
        font-weight: 500;
        margin-top: 8px;
        transition: all .5s;


    }

    .rate{
        color: #657282;
        display: flex;
        gap: 8px;
        align-items: center;
    }
</style>
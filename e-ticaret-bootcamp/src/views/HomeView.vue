<template>
    <div class="filterWrapper">
        <div class="flex">
            <div @click="activeCategory = activeCategory === item 
            ? '':item" 
            :class="activeCategory === item ? 'activeCategory' : ''"
            class="category" v-for="item in categories" :key="item.id">
                {{ item }}
            </div>
        </div>
        <div @click="sortMode = sortMode === 'asc' ? 'desc' : 'asc' " class="order">Sırala {{ sortMode === "asc" ? "A-Z" : "Z-A" }}
        </div>
    </div>
    <div class="grid">
        <ProductCard @onClickBox = "onClickBox($event)" v-for="item in data" :key="item" :item = "item" />
       <div v-for="item in data" :key="item"></div>
    </div>
</template>

<script>
    import ProductCard from '@/components/ProductCard.vue'

    export default{
        name:"HomePage",
        components:{
            ProductCard
        },
        created(){
            this.getAllCategories()
            this.getAllProducts()
        },
        methods:{
            onClickBox(data){
                this.$store.dispatch('addBaskets',data)
            },
            getProductByCategory(category){
                fetch('https://fakestoreapi.com/products/category/'+category+"?sort="+this.sortMode)
                .then(res=>res.json())
                .then(json=>{
                    this.data = json
                })
            },
            getAllCategories(){
                fetch('https://fakestoreapi.com/products/categories')
                .then(res=>res.json())
                .then(json=>{
                    this.categories = json
                })
            },
            getAllProducts(){
                fetch('https://fakestoreapi.com/products?sort'+this.sortMode)
                .then(res=>res.json())
                .then(json=>{
                    this.data = json
                })
            }
        },
        data(){
            return{
                data:[],
                activeCategory:"",
                categories:[],
                sortMode:"asc"
            }
        },
        watch:{
            sortMode(){
                if(this.activeCategory === ""){
                    this.getAllProducts()
                }
                else{
                    this.getProductByCategory(this.activeCategory.toLowerCase())
                }

            },
            activeCategory(newVal,oldVal){
                if(newVal===""){
                    this.getAllProducts()
                }
                else{
                    this.getProductByCategory(newVal.toLowerCase())
                }
                console.log(newVal,oldVal)

            }
        }
    }
</script>

<style scoped>
    .grid{
        display: grid;
        grid-template-columns: repeat(5,1fr);
        gap: 20px;
    }

    .filterWrapper{
        display: flex;
        align-items: center;
        margin-bottom: 20px;
        justify-content: space-between;
    }

    .flex{
        display: flex;
        align-items: center;
        gap: 20px;
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

    .activeCategory{
        transition: all .5s;
        border: 1px solid #96999B;
        font-weight: 600;
    }

    .order{
        cursor: pointer;

    }

</style>
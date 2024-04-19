import {createRouter,createWebHistory} from 'vue-router'
import HomePage from '../views/HomeView.vue'
import ProductDetail from '../views/ProductDetailView.vue'
import BasketPreview from '../views/BasketPreviewView.vue'




const routes = [
    {
        path:'/',
        component:HomePage
    },
    {
        path:'/product-detail/:id',
        component:ProductDetail
    },
    {
        path:'/basket-preview',
        component:BasketPreview
    }
]

const router = createRouter({
    history:createWebHistory(),
    routes
})

export default router
import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || ''
const API_KEY = import.meta.env.VITE_AURA_API_KEY || 'dev_secret_key'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 
    'Content-Type': 'application/json',
    'X-API-Key': API_KEY
  },
})

client.interceptors.response.use(
  res => res,
  err => {
    console.error('[Aura API]', err.message)
    return Promise.reject(err)
  }
)

export default client

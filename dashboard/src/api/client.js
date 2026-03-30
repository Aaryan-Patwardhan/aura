import axios from 'axios'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const client = axios.create({
  baseURL: API_BASE,
  timeout: 10000,
  headers: { 'Content-Type': 'application/json' },
})

client.interceptors.response.use(
  res => res,
  err => {
    console.error('[Aura API]', err.message)
    return Promise.reject(err)
  }
)

export default client

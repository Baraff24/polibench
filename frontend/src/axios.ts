import axios from 'axios'

// Request interceptor: aggiunge il token Bearer a ogni richiesta
axios.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('token')
    if (token) {
      config.headers['Authorization'] = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error),
)

// Response interceptor: su 401 pulisce il token scaduto/invalido dal localStorage.
// Questo evita che token vecchi (es. dopo un reset del DB) causino loop di errori.
axios.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
    }
    return Promise.reject(error)
  },
)

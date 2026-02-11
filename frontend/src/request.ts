import axios from 'axios';

const baseURL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

let config = {};

if (baseURL !== '') {
  config = {
    baseURL,
    withCredentials: true,
  };
}

export const request = axios.create(config);

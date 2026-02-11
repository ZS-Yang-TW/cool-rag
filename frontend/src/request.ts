import axios from 'axios';
const baseURL = import.meta.env.VITE_API_URL;

let config = {};

if (baseURL !== '') {
  config = {
    baseURL,
    // TODO: Set withCredentials to true if backend requires cookies for authentication
    withCredentials: false,
  };
}

export const request = axios.create(config);

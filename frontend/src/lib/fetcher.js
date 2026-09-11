import { api } from "./api";

const swrFetcher = async (path) => {
  return api.get(path);
};

export {
  swrFetcher
};

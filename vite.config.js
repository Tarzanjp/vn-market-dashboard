import { resolve } from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig(({ command }) => ({
  // GitHub Pages serves this repo from https://tarzanjp.github.io/vn-market-dashboard/
  // (a project page, not a user/org root page) — asset URLs and the SPA's own runtime
  // fetch()/href paths must be prefixed with this subpath in the production build.
  // Dev server stays at "/" so `npm run dev` keeps working at http://localhost:5173/.
  base: command === "build" ? "/vn-market-dashboard/" : "/",
  plugins: [react()],
  build: {
    rollupOptions: {
      input: {
        regime: resolve(__dirname, "buc-tranh-thi-truong.html"),
        main: resolve(__dirname, "index.html"),
        theGioi: resolve(__dirname, "the-gioi.html"),
        lichSu: resolve(__dirname, "lich-su.html"),
        dongTienNganh: resolve(__dirname, "dong-tien-nganh.html"),
        dongTienCashout: resolve(__dirname, "dong-tien-cashout.html"),
        huongDanDoc: resolve(__dirname, "huong-dan-doc.html"),
      },
    },
  },
}));

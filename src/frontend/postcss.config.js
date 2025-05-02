import tailwindcss from "tailwindcss";
import autoprefixer from "autoprefixer";

/** @type {import('postcss-load-config').Config} */
export default {
  plugins: [
    //Some plugins, like tailwindcss/nesting, need to run before Tailwind,
    tailwindcss,
    //But others, like autoprefixer, need to run after,
    autoprefixer,
  ],
};

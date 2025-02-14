// export default {
//   plugins: [],
//   svelte: {
//     preprocess: [],
//   },
//   build: {
//     target: "modules",
//   },
// };

import commonjs from "vite-plugin-commonjs";

export default {
  plugins: [
    commonjs({
      filter(id) {
        return id.includes("node_modules/deepmerge");
      },
    }),
  ],
  svelte: {
    preprocess: [],
  },
  build: {
    target: "modules",
  },
};

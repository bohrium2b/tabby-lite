module.exports = {
  plugins: [
    require('postcss-import'),
    require('@tailwindcss/postcss'),
    require('autoprefixer'),
    require('postcss-url')({
      url: 'copy',
      // This is where the actual .woff2 files will be moved
      assetsPath: 'fonts', 
      // This ensures the CSS points to the right place in Django
      useHash: true 
    }),
  ],
};
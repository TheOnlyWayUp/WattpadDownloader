The fonts need to be symlinked to /tmp/fonts, this allows the fonts to be loaded during development and during build-time.
It's assumed fonts will be present at `/tmp/fonts`, during development they're at `/src/api/src/create_book/generators/pdf`, and during deployment they're at `/app/src/api/src/create_book/generators/pdf`. This seems like a clean solution.

`Fontconfig error: Cannot load default config file: No such file: (null)`
If the fonts aren't found, this warning pops up in console. It won't cause downloads to fail, though.

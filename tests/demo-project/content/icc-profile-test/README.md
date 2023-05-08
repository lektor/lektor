# ICC Profile Tests

## Color-rotated test image

The `rgb-to-gbr-test.jpg` test image comes from
[codelogic/wide-gamut-tests](https://github.com/codelogic/wide-gamut-tests)
and is licensed under an Apache license. To save on storage space,
the version included here is scaled to 200x200 pixels (from the
original 1000x1000 pixels).

It has an embedded color space that rotates blue to red, etc. If
color spaces are handled correctly the displayed colors should agree
with the displayed color names.

## Sample CMYK ICC Profile

The `CGATS001Compat-v2-micro.icc` profile is the smallest CMYK ICC
profile I could find. It comes from
[saucecontrol/Compact-ICC-Profiles](https://github.com/saucecontrol/Compact-ICC-Profiles)
and is made available under a
[CC0-1.0](https://creativecommons.org/publicdomain/zero/1.0/) license.

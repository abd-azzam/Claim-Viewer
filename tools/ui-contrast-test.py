"""WCAG contrast checks for the existing tokens used by the new provider/Word UI."""
def luminance(value):
    rgb = [int(value[i:i+2], 16)/255 for i in (1, 3, 5)]
    rgb = [c/12.92 if c <= .03928 else ((c+.055)/1.055)**2.4 for c in rgb]
    return sum(c*w for c, w in zip(rgb, (.2126, .7152, .0722)))

themes = {
    'light': dict(bg='#ffffff', panel='#f6f7f9', ink='#15181d', mute='#5d6672', acc='#1f5fbf', ctl='#767f8c'),
    'dark': dict(bg='#14171c', panel='#1c2027', ink='#e8ebef', mute='#9aa4b0', acc='#7aa7ff', ctl='#6b7684'),
}
count = 0
for theme, colors in themes.items():
    for background in ('bg', 'panel'):
        for foreground in ('ink', 'mute', 'acc', 'ctl'):
            a, b = sorted([luminance(colors[foreground]), luminance(colors[background])])
            ratio = (b+.05)/(a+.05)
            threshold = 3 if foreground == 'ctl' else 4.5
            assert ratio >= threshold, (theme, foreground, background, ratio)
            count += 1
print(f'{count} theme-token pairings PASS: text >=4.5:1, interactive borders >=3:1.')

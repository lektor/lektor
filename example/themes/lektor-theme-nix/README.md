# Nix

Nix is a simple, minimal theme for [Lektor](https://www.getlektor.com/) based in [Nix hugo theme](https://github.com/LordMathis/hugo-theme-nix)

# Configuration

Create a `404.html/contents.lr` content file pointing to 404.html, using a none model [see Lektor docs](https://www.getlektor.com/docs/guides/error-pages)

Create a `contents.lr` content file pointing to index.html, using a none model

Add lektor-disqus-comments plugin an configure it https://github.com/lektor/lektor-disqus-comments#lektor-disqus-comments

Add params in the `.lektorproject file`

```ini
[theme_settings]
  githubID = "your_github"
  gitlabId = "your_gitlab"
  twitterID = "your_twitter"
  codepenID = "your_codepen"
  linkedInID = "your_linkedin"
  googleplusID = "your_googleplus"
  facebookID = "your_facebook"
  instagramID = "your_instagram"
  telegramID = "your_telegram"
  name = "your_name"
  headerusername = "username"
  headerhostname = "hostname"
  email = "your_email"
  about = "info_about_you"
  profilepicture = "profile_picture_asset_url"
  googleanalytics = "your_google_analytics_id"
  slackURL = "https://join.slack.com/..."
  comments = "yes"
```

Add your profile picture in the assets folder and set the path in `profilepicture` (e.g. `img/myprofilepicture.png`)

## License

Nix is licensed under the [MIT License](LICENSE.md)

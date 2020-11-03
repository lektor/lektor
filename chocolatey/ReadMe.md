# Lektor Chocolatey Package

To install the package from chocolatey:

```powershell
choco install lektor
```

To run the package locally, install these commands from :

```powershell
git clone https://github.com/lektor/lektor.git
cd chocolatey
choco pack
choco install -fdv
```

To push the updated package to chocolatey:

```powershell
choco apikey --key <apikey> --source https://push.chocolatey.org/
choco push lektor.<version>.nupkg --source https://push.chocolatey.org/
```

# Updall

## What is this?

A utility that runs my daily operating system and software updates.  

For as long as I can remember, I have manually updated all of the software on all of my computers, usually Linux, sometimes macOS, rarely Windows.  

It is most easily expressed in the bash aliases that I use. One of the tricky parts here is that these require `sudo` access.

On my Arch Linux laptop:

```bash
alias updall='date; paru && paru -Sua && rustup update && cargo install-update -a && sdk selfupdate && sdk update && sdk upgrade && npm update -g && cd && gcloud components update && date'
```

This displays the date; runs the AUR helper `paru` to update all installed packages, including system packages, those installed with `pacman`, and those installed from the AUR; checks my Rust toolchain for available updates and applies them if available; runs the `cargo install-update -a` command to invoke the `cargo-update` crate to update all installed Rust crates; invokes SDKman's self-update, checks its installed SDK's and updates those; updates node.js packages with `npm`; updates my GCP toolchain; displays the date when complete.  

I have a similar alias for my home server, also Arch Linux; it lacks only the GCP updates because I do not use GCP from the server.

On my Arch Linux home server:

```bash
alias updall='date; paru && paru -Sua && rustup update && cargo install-update -a && sdk selfupdate && sdk update && sdk upgrade && npm update -g; date'
```

I have a similar alias for my VPS running Debian Linux. Note that it invokes the appropriate package management system, `apt` in this case, instead of `paru` on my Arch Linux systems.

On my Debian Linux VPS:

```bash
alias updall='date; sudo apt update && sudo apt upgrade && sudo apt autoremove && rustup update && cargo install-update -a && sdk selfupdate && sdk update && sdk upgrade && npm update -g; date'
```

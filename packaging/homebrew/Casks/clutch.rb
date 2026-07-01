# Clutch — Homebrew Cask
# Install from a cloned repo:
#   brew install --cask ./packaging/homebrew/Casks/clutch.rb
#
# After the tap repo is published (fancy1108/homebrew-clutch):
#   brew tap fancy1108/clutch
#   brew install --cask clutch
#
# Bump version + sha256 on each release (see docs/PACKAGE_MANAGERS.md).

cask "clutch" do
  version "1.0.2"
  sha256 "982b768608ece0dbd659abbc1dfc70f00185f8c07a8287d0a41165a43df49b7f"

  url "https://github.com/fancy1108/Clutch/releases/download/v#{version}/Clutch_#{version.tr(".", "_")}_aarch64.dmg"
  name "Clutch"
  desc "Local AI multi-agent orchestration and supervision desktop app"
  homepage "https://github.com/fancy1108/Clutch"

  depends_on macos: ">= :sonoma"
  depends_on arch: :arm64

  app "Clutch.app"

  postflight do
    system_command "/usr/bin/xattr",
                   args: ["-cr", "#{appdir}/Clutch.app"],
                   print_stderr: false
  end

  caveats <<~EOS
    Clutch is currently distributed unsigned (Gatekeeper). If launch is blocked:
      xattr -cr /Applications/Clutch.app && open -a Clutch

    Intel Mac DMG is not published yet — Apple Silicon only.
  EOS

  zap trash: [
    "~/Library/Application Support/clutch",
    "~/Library/Application Support/clutch_dev",
  ]
end

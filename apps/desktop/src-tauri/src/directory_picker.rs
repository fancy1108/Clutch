//! Native directory picker. macOS enables hidden folders (e.g. ~/.cursor/skills).

use std::path::PathBuf;

pub fn pick_directory(
    title: &str,
    default_path: Option<&str>,
    show_hidden: bool,
) -> Option<PathBuf> {
    #[cfg(target_os = "macos")]
    {
        return macos::pick_directory(title, default_path, show_hidden);
    }

    #[cfg(not(target_os = "macos"))]
    {
        let _ = (title, default_path, show_hidden);
        None
    }
}

#[cfg(target_os = "macos")]
mod macos {
    use super::PathBuf;
    use objc2::rc::autoreleasepool;
    use objc2::MainThreadMarker;
    use objc2_app_kit::{NSModalResponseOK, NSOpenPanel};
    use objc2_foundation::{NSString, NSURL};

    pub fn pick_directory(
        title: &str,
        default_path: Option<&str>,
        show_hidden: bool,
    ) -> Option<PathBuf> {
        autoreleasepool(|_| {
            dispatch2::run_on_main(|mtm| open_panel(mtm, title, default_path, show_hidden))
        })
    }

    fn open_panel(
        mtm: MainThreadMarker,
        title: &str,
        default_path: Option<&str>,
        show_hidden: bool,
    ) -> Option<PathBuf> {
        let panel = NSOpenPanel::openPanel(mtm);
        panel.setCanChooseDirectories(true);
        panel.setCanChooseFiles(false);
        panel.setShowsHiddenFiles(show_hidden);
        panel.setCanCreateDirectories(true);
        panel.setMessage(Some(&NSString::from_str(title)));
        if let Some(path) = default_path {
            let url = NSURL::fileURLWithPath_isDirectory(&NSString::from_str(path), true);
            panel.setDirectoryURL(Some(&url));
        }

        let response = panel.runModal();
        if response != NSModalResponseOK {
            return None;
        }

        let url = panel.URL()?;
        let path = url.path()?;
        Some(PathBuf::from(path.to_string()))
    }
}

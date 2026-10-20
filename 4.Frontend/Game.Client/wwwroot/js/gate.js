// The free web game opens only for visitors who come from scottcoxdev.com (ADR 0041). Anyone else
// gets a short page pointing there. It stops casual visits and copycat links, not a determined
// person: the check runs in the browser. Only the live site is gated, so local runs, previews,
// staging and the browser tests are not. Pages that emails link to, and the legal and status
// pages, always open.
window.gameGate = (() => {
    const gatedHost = "play.scottcoxdev.com";
    const homeUrl = "https://scottcoxdev.com/";
    const storageKey = "arena-launched";
    const openPaths = ["/confirm-email", "/reset-password", "/forgot-password", "/privacy", "/terms", "/status"];

    const cameFromSite = () => {
        try {
            const host = new URL(document.referrer).hostname;
            return host === "scottcoxdev.com" || host.endsWith(".scottcoxdev.com");
        } catch {
            return false;
        }
    };

    const remembered = () => {
        try { return localStorage.getItem(storageKey) === "1"; } catch { return false; }
    };

    const remember = () => {
        try { localStorage.setItem(storageKey, "1"); } catch { /* private window: works for this visit only */ }
    };

    const isOpenPath = () => openPaths.some(p => location.pathname.toLowerCase().startsWith(p));

    let allowed = true;
    if (location.hostname === gatedHost && !isOpenPath()) {
        if (cameFromSite()) {
            remember();
        } else if (!remembered()) {
            allowed = false;
        }
    }

    const showGate = () => {
        const app = document.getElementById("app");
        app.innerHTML =
            '<main style="max-width:32rem;margin:15vh auto 0;padding:0 1rem;text-align:center">' +
            '<h1 style="font-size:2rem">Kings of the Card Arena</h1>' +
            '<p style="font-size:1.2rem">The game is played from scottcoxdev.com.</p>' +
            '<a class="btn btn-primary btn-lg" href="' + homeUrl + '">Go to scottcoxdev.com</a>' +
            '</main>';
    };

    return {
        allowed,
        // Called once Blazor's script has loaded (index.html starts it with autostart="false").
        start: () => {
            if (allowed) {
                Blazor.start();
            } else {
                showGate();
            }
        }
    };
})();

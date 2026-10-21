import { useCallback, useEffect, useState } from "react";
import { Search, Bell, Sun, Moon, X } from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import notificationsApi from "../../api/notifications";
import ProfileDropdown from "./ProfileDropdown";

export default function Topbar({ searchPlaceholder = "Search leads, customers, projects..." }) {
  const { theme, toggleTheme } = useTheme();
  const isDark = theme === "dark";
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [loading, setLoading] = useState(false);
  const [loadingMore, setLoadingMore] = useState(false);
  const [hasMore, setHasMore] = useState(false);
  const [loadError, setLoadError] = useState("");

  const loadNotifications = useCallback(async (markRead = false) => {
    setLoading(true);
    setLoadError("");
    try {
      const [notifications, unread] = await Promise.all([
        notificationsApi.getNotifications({ limit: 20 }),
        notificationsApi.getUnreadCount(),
      ]);
      const page = notifications || [];
      setItems(page.map((item) => ({
        ...item,
        read: item.is_read,
      })));
      setHasMore(page.length === 20);
      setUnreadCount(unread?.unread_count || 0);

      if (markRead && unread?.unread_count > 0) {
        await notificationsApi.markAllRead();
        setItems((current) => current.map((item) => ({ ...item, read: true, is_read: true })));
        setUnreadCount(0);
      }
    } catch (error) {
      setLoadError(error.message || "Unable to load notifications.");
    } finally {
      setLoading(false);
    }
  }, []);

  async function handleLoadMore() {
    setLoadingMore(true);
    setLoadError("");
    try {
      const page = await notificationsApi.getNotifications({
        limit: 20,
        offset: items.length,
      });
      setItems((current) => {
        const knownIds = new Set(current.map((item) => item.id));
        const newItems = (page || [])
          .filter((item) => !knownIds.has(item.id))
          .map((item) => ({ ...item, read: item.is_read }));
        return [...current, ...newItems];
      });
      setHasMore((page || []).length === 20);
    } catch (error) {
      setLoadError(error.message || "Unable to load more notifications.");
    } finally {
      setLoadingMore(false);
    }
  }

  useEffect(() => {
    loadNotifications();
  }, [loadNotifications]);

  function handleToggleNotifications() {
    const nextOpen = !open;
    setOpen(nextOpen);
    if (nextOpen) {
      loadNotifications(true);
    }
  }

  return (
    <header className="flex items-center gap-4 px-5 sm:px-8 py-4 bg-white dark:bg-[#152019] border-b border-line dark:border-[#293227] sticky top-0 z-10 transition-colors duration-200">
      <div className="relative flex-1 max-w-md">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-400 dark:text-gray-400" />
        <input
          type="text"
          placeholder={searchPlaceholder}
          className="w-full pl-9 pr-4 py-2.5 rounded-lg bg-[#f4f6f4] dark:bg-[#0E1712] border border-transparent dark:border-[#293227] text-sm text-ink-900 dark:text-white placeholder:text-ink-400 dark:placeholder:text-gray-400 focus:outline-none focus:ring-2 focus:ring-leaf-500/30 focus:bg-white dark:focus:bg-[#0E1712] focus:border-line dark:focus:border-leaf-600 transition-colors"
        />
      </div>

      <div className="ml-auto flex items-center gap-3 sm:gap-4">
        <button
          type="button"
          onClick={toggleTheme}
          className="w-9 h-9 rounded-full border border-line dark:border-[#293227] flex items-center justify-center bg-white dark:bg-[#0E1712] text-ink-600 dark:text-gray-200 hover:border-leaf-500 transition-colors focus:outline-none"
          aria-label="Toggle Theme"
          title={isDark ? "Switch to Light Mode" : "Switch to Dark Mode"}
        >
          {isDark ? (
            <Sun className="w-4 h-4 text-amber-400" />
          ) : (
            <Moon className="w-4 h-4 text-[#1F5C3E]" />
          )}
        </button>

        <div className="relative">
          <button
            type="button"
            onClick={handleToggleNotifications}
            className="relative w-9 h-9 grid place-items-center rounded-full bg-[#f4f6f4] dark:bg-[#0E1712] border border-transparent dark:border-[#293227] hover:bg-line dark:hover:bg-[#293227] transition-colors"
            aria-label="Notifications"
            title="Notifications"
          >
            <Bell className="w-[18px] h-[18px] text-ink-600 dark:text-gray-200" />
            {unreadCount > 0 && (
              <span className="absolute -top-0.5 -right-0.5 w-[18px] h-[18px] grid place-items-center rounded-full bg-red-500 text-white text-[10px] font-semibold">
                {unreadCount}
              </span>
            )}
          </button>

          {open && (
            <div className="absolute right-0 top-12 w-80 rounded-2xl border border-line bg-white dark:bg-[#17221B] shadow-xl z-20 overflow-hidden">
              <div className="flex items-center justify-between border-b border-line px-4 py-3">
                <h3 className="text-sm font-semibold text-ink-900 dark:text-white">Notifications</h3>
                <button
                  type="button"
                  onClick={() => setOpen(false)}
                  className="rounded p-1 text-ink-500 hover:bg-[#f4f6f4] dark:hover:bg-[#0E1712]"
                  aria-label="Close notifications"
                >
                  <X className="w-4 h-4" />
                </button>
              </div>

              <div className="max-h-80 overflow-y-auto">
                {loading ? (
                  <p className="px-4 py-6 text-center text-xs text-ink-500">Loading notifications...</p>
                ) : loadError ? (
                  <p role="alert" className="px-4 py-6 text-center text-xs text-red-600">{loadError}</p>
                ) : items.length === 0 ? (
                  <p className="px-4 py-6 text-center text-xs text-ink-500">You have no notifications.</p>
                ) : items.map((item) => (
                  <div key={item.id} className={`border-b border-line px-4 py-3 last:border-b-0 ${item.read ? "opacity-75" : "bg-[#f7faf7] dark:bg-[#0f1a14]"}`}>
                    <div className="flex items-start justify-between gap-3">
                      <div>
                        <p className="text-sm font-semibold text-ink-900 dark:text-white">{item.title}</p>
                        <p className="mt-1 text-xs text-ink-600 dark:text-[#B9C4BB]">{item.message}</p>
                      </div>
                      {!item.read && <span className="mt-1 h-2.5 w-2.5 rounded-full bg-red-500" />}
                    </div>
                    <p className="mt-2 text-[11px] text-ink-500 dark:text-[#8A968C]">{item.time}</p>
                  </div>
                ))}
                {!loading && !loadError && hasMore && (
                  <button
                    type="button"
                    onClick={handleLoadMore}
                    disabled={loadingMore}
                    className="w-full px-4 py-3 text-xs font-medium text-leaf-700 hover:bg-[#f4f6f4] disabled:opacity-60 dark:text-leaf-400 dark:hover:bg-[#0E1712]"
                  >
                    {loadingMore ? "Loading..." : "Load more"}
                  </button>
                )}
              </div>
            </div>
          )}
        </div>

        <ProfileDropdown />
      </div>
    </header>
  );
}

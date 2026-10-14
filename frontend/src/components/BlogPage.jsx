import React, { useState, useEffect } from 'react';
import { Clock, Calendar, ArrowRight } from 'lucide-react';
import Eyebrow from './Eyebrow';
import CtaBanner from './CtaBanner';
import { blogsApi } from '../api/blogs';

export default function BlogPage({ theme }) {
  const [posts, setPosts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  useEffect(() => {
    async function fetchBlogs() {
      setLoading(true);
      try {
        const res = await blogsApi.getBlogs({ status: "Published", limit: 20 });
        const items = Array.isArray(res) ? res : res.items || [];
        setPosts(items);
      } catch (err) {
        setError(err.message || "Failed to load blog posts.");
      } finally {
        setLoading(false);
      }
    }
    fetchBlogs();
  }, []);

  const featuredPost = posts[0] ? {
    category: posts[0].category || 'Technology',
    title: posts[0].title,
    excerpt: posts[0].excerpt || posts[0].content?.slice(0, 150) || '',
    date: posts[0].created_at ? new Date(posts[0].created_at).toLocaleDateString() : 'Recent',
    readTime: '5 min read',
    image: posts[0].cover_image || posts[0].coverImage || 'https://placehold.co/700x400/EFF3EC/1F5C3E?text=Solar+Article',
  } : null;

  const remainingPosts = posts.slice(1).map((post) => ({
    id: post.id,
    category: post.category || 'Guides',
    title: post.title,
    excerpt: post.excerpt || post.content?.slice(0, 120) || '',
    date: post.created_at ? new Date(post.created_at).toLocaleDateString() : 'Recent',
    readTime: '4 min read',
    image: post.cover_image || post.coverImage || 'https://placehold.co/500x320/EFF3EC/1F5C3E?text=Solar+Article',
  }));

  return (
    <div className="transition-colors duration-200" style={{ backgroundColor: theme.bg }}>
      <section className="py-12 sm:py-16 lg:py-20">
        <div className="max-w-[1280px] mx-auto px-4 sm:px-6 lg:px-8 xl:px-10">
          <Eyebrow text="Insights" theme={theme} />
          <h1
            className="text-4xl sm:text-5xl lg:text-[54px] font-semibold leading-[1.15] tracking-tight max-w-4xl"
            style={{ color: theme.text }}
          >
            Latest from the Solara blog
          </h1>

          {loading && (
            <div className="py-16 text-center text-sm" style={{ color: theme.textMuted }}>
              Loading blog articles...
            </div>
          )}

          {error && (
            <div className="my-6 p-4 rounded-2xl bg-red-50 border border-red-200 text-sm text-red-700">
              {error}
            </div>
          )}

          {!loading && featuredPost && (
            <div
              className="mt-10 sm:mt-12 rounded-3xl overflow-hidden border transition-all duration-200 grid grid-cols-1 lg:grid-cols-12 group"
              style={{
                backgroundColor: theme.card,
                borderColor: theme.border,
              }}
            >
              <div className="lg:col-span-7 relative min-h-[260px] sm:min-h-[340px] lg:min-h-[400px] overflow-hidden">
                <img
                  src={featuredPost.image}
                  alt={featuredPost.title}
                  loading="lazy"
                  className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                />
              </div>

              <div className="lg:col-span-5 p-6 sm:p-8 lg:p-10 flex flex-col justify-between">
                <div>
                  <div className="mb-4">
                    <span
                      className="inline-block px-3 py-1 text-xs font-bold rounded-full border tracking-wide uppercase"
                      style={{
                        backgroundColor: theme.greenSoft,
                        color: theme.green,
                        borderColor: theme.border,
                      }}
                    >
                      {featuredPost.category}
                    </span>
                  </div>

                  <h2
                    className="text-2xl sm:text-3xl font-bold tracking-tight leading-snug group-hover:underline decoration-2"
                    style={{ color: theme.text }}
                  >
                    {featuredPost.title}
                  </h2>

                  <p
                    className="mt-4 text-base leading-relaxed"
                    style={{ color: theme.textMuted }}
                  >
                    {featuredPost.excerpt}
                  </p>
                </div>

                <div
                  className="mt-6 pt-6 border-t flex items-center justify-between text-xs sm:text-sm font-medium"
                  style={{
                    borderColor: theme.border,
                    color: theme.textFaint,
                  }}
                >
                  <div className="flex items-center gap-1.5">
                    <Calendar className="w-4 h-4" />
                    <span>{featuredPost.date}</span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Clock className="w-4 h-4" />
                    <span>{featuredPost.readTime}</span>
                  </div>
                </div>
              </div>
            </div>
          )}

          {!loading && remainingPosts.length > 0 && (
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 sm:gap-8 mt-10 sm:mt-14">
              {remainingPosts.map((post) => (
                <div
                  key={post.id}
                  className="rounded-2xl overflow-hidden border transition-all duration-200 flex flex-col justify-between group"
                  style={{
                    backgroundColor: theme.card,
                    borderColor: theme.border,
                  }}
                >
                  <div>
                    <div className="h-48 sm:h-52 overflow-hidden relative">
                      <img
                        src={post.image}
                        alt={post.title}
                        loading="lazy"
                        className="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
                      />
                    </div>

                    <div className="p-6">
                      <div className="mb-3">
                        <span
                          className="inline-block px-2.5 py-0.5 text-xs font-bold rounded-full border tracking-wide uppercase"
                          style={{
                            backgroundColor: theme.greenSoft,
                            color: theme.green,
                            borderColor: theme.border,
                          }}
                        >
                          {post.category}
                        </span>
                      </div>

                      <h3
                        className="text-lg font-bold tracking-tight leading-snug group-hover:underline decoration-2"
                        style={{ color: theme.text }}
                      >
                        {post.title}
                      </h3>

                      <p
                        className="mt-2.5 text-sm leading-relaxed"
                        style={{ color: theme.textMuted }}
                      >
                        {post.excerpt}
                      </p>
                    </div>
                  </div>

                  <div
                    className="px-6 py-4 border-t flex items-center justify-between text-xs font-medium mt-auto"
                    style={{
                      borderColor: theme.border,
                      color: theme.textFaint,
                    }}
                  >
                    <div className="flex items-center gap-1.5">
                      <Calendar className="w-3.5 h-3.5" />
                      <span>{post.date}</span>
                    </div>
                    <div className="flex items-center gap-1.5">
                      <Clock className="w-3.5 h-3.5" />
                      <span>{post.readTime}</span>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {!loading && posts.length === 0 && (
            <div className="py-16 text-center text-sm" style={{ color: theme.textMuted }}>
              No published articles available at this time.
            </div>
          )}
        </div>
      </section>

      <CtaBanner theme={theme} />
    </div>
  );
}

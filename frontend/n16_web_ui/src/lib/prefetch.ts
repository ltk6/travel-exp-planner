/**
 * Utility to prefetch images for the top recommended locations.
 * By fetching the primary images of the top 5 locations in parallel immediately
 * after the recommendation endpoint returns, they will be warmed up in the
 * browser's HTTP cache by the time the results page mounts.
 */
export function prefetchLocationImages(data: { locations?: Array<{ images?: string[] }> }) {
  if (typeof window === "undefined") return;

  const topLocations = data.locations?.slice(0, 5) ?? [];
  topLocations.forEach((loc) => {
    const url = loc.images?.[0];
    if (url) {
      const img = new Image();
      img.src = url;
    }
  });
}

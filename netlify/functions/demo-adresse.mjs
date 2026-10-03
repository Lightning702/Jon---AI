export default async () => {
  const url = (process.env.JON_DEMO_URL || "").replace(/\/$/, "");
  return new Response(JSON.stringify({url}), {headers: {"Content-Type": "application/json; charset=utf-8", "Cache-Control": "public, max-age=60"}});
};

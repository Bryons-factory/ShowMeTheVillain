export interface Env {
  DB: D1Database; 
}

export default {
  async scheduled(event: ScheduledEvent, env: Env, ctx: ExecutionContext) {
    
    // Fetch the latest data from the PhishStats API
    const response = await fetch("https://phishstats.info/api/..."); 
    const phishingData = await response.json();

    const statements = [];
    
    // Map the JSON array to the required schema fields
    for (const item of phishingData) {
      const stmt = env.DB.prepare(
        "INSERT INTO phishing_points (lat, lon, intensity, name, threat_level, company, country, isp) VALUES (?, ?, ?, ?, ?, ?, ?, ?)"
      ).bind(
        item.lat, 
        item.lon, 
        item.intensity, 
        item.name, 
        item.threat_level, 
        item.company, 
        item.country, 
        item.isp
      );
      statements.push(stmt);
    }

    // Execute all insertions atomically using a batch transaction
    if (statements.length > 0) {
      await env.DB.batch(statements);
    }
    
    console.log(`Successfully inserted ${statements.length} records.`);
  }
};

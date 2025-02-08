import fetch from "node-fetch";
import moment from "moment";
import queryString from "query-string";

const getTimelineURL = "https://api.tomorrow.io/v4/timelines";
const apikey = "yrrmklvlF6XsNGzrtbQEQT1CNAzdCfBm";

const fetchWeatherData = async (coordinates) => {
  const params = queryString.stringify({
    apikey,
    location: coordinates,
    fields: ["temperature", "precipitationIntensity", "windSpeed"],
    timesteps: "1h",
    units: "imperial",
    startTime: moment().utc().startOf("hour").toISOString(),
    endTime: moment().utc().startOf("hour").add(2, "hours").toISOString(),
  });

  try {
    const response = await fetch(`${getTimelineURL}?${params}`, {
      headers: {
        "Accept-Encoding": "gzip",
        Accept: "application/json",
      },
    });

    if (!response.ok) {
      throw new Error(`Weather API error: ${response.status}`);
    }

    return response.json();
  } catch (error) {
    console.error("Fetch error:", error);
    throw error;
  }
};

const main = async () => {
  try {
    const [requestType, coordinates] = process.argv.slice(2);

    if (requestType === "weather") {
      const result = await fetchWeatherData(coordinates);
      console.log(JSON.stringify(result));
    }
  } catch (error) {
    console.error(JSON.stringify({ error: error.message }));
    process.exit(1);
  }
};

main();

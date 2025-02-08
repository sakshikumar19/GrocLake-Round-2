const { execSync } = require("child_process");

try {
  execSync(
    "npm install node-fetch@2.6.7 moment@2.29.4 query-string@7.1.1 --save",
    { stdio: "inherit" }
  );
} catch (error) {
  console.error("Error installing packages:", error);
  process.exit(1);
}

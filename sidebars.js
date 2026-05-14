/** @type {import('@docusaurus/plugin-content-docs').SidebarsConfig} */
const sidebars = {
  docsSidebar: [
    {type: "doc", id: "index", label: "Home"},
    {type: "doc", id: "getting-started", label: "Getting Started"},
    {type: "doc", id: "cli", label: "CLI Reference"},
    {type: "doc", id: "configuration", label: "Configuration Reference"},
    {type: "doc", id: "database", label: "Database and Migrations"},
    {
      type: "doc",
      id: "spring-dotnet-module-structure",
      label: "Spring and .NET Module Guide",
    },
    {type: "doc", id: "architecture", label: "Architecture"},
    {type: "doc", id: "architecture-diagram", label: "Architecture Diagram"},
    {type: "doc", id: "agent-recommendation", label: "Agent Recommendation Guide"},
    {type: "doc", id: "project-checks", label: "Project Checks"},
    {type: "doc", id: "feature-status", label: "Feature Status"},
    {
      type: "category",
      label: "Integrations",
      items: [
        {type: "doc", id: "integrations/index", label: "Overview"},
        {type: "doc", id: "integrations/kafka", label: "Kafka"},
        {type: "doc", id: "integrations/rabbitmq", label: "RabbitMQ"},
        {type: "doc", id: "integrations/llm", label: "LLM"},
      ],
    },
    {
      type: "category",
      label: "Examples",
      items: [
        {type: "doc", id: "examples/index", label: "Overview"},
        {type: "doc", id: "examples/user-registration", label: "User Registration"},
        {type: "doc", id: "examples/auth-foundation", label: "Auth Foundation"},
        {type: "doc", id: "examples/html-swap", label: "HTML Swap"},
      ],
    },
    {type: "doc", id: "troubleshooting", label: "Troubleshooting and FAQ"},
    {type: "doc", id: "release-upgrade-notes", label: "Release and Upgrade Notes"},
  ],
};

module.exports = sidebars;

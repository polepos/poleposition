const {themes: prismThemes} = require("prism-react-renderer");

/** @type {import('@docusaurus/types').Config} */
const config = {
  title: "PolePosition",
  tagline: "Project lifecycle CLI for starting and growing enterprise FastAPI projects",
  favicon: "assets/logo/poleposition-fav.png",

  url: "https://erenertemden.github.io",
  baseUrl: "/poleposition/",

  organizationName: "erenertemden",
  projectName: "poleposition",
  trailingSlash: false,

  onBrokenLinks: "throw",
  onBrokenMarkdownLinks: "throw",
  onBrokenAnchors: "throw",

  i18n: {
    defaultLocale: "en",
    locales: ["en"],
  },

  presets: [
    [
      "classic",
      {
        docs: {
          path: "docs",
          routeBasePath: "/",
          sidebarPath: require.resolve("./sidebars.js"),
          editUrl: "https://github.com/erenertemden/poleposition/edit/main/docs/",
          showLastUpdateTime: true,
        },
        blog: false,
        theme: {
          customCss: require.resolve("./src/css/custom.css"),
        },
      },
    ],
  ],

  themeConfig: {
    image: "assets/logo/poleposition-logo.png",
    colorMode: {
      defaultMode: "light",
      respectPrefersColorScheme: true,
    },
    navbar: {
      title: "PolePosition",
      logo: {
        alt: "PolePosition logo",
        src: "assets/logo/poleposition-logo.png",
      },
      items: [
        {to: "/getting-started", label: "Getting Started", position: "left"},
        {to: "/cli", label: "CLI", position: "left"},
        {to: "/database", label: "Database", position: "left"},
        {to: "/integrations/", label: "Integrations", position: "left"},
        {
          href: "https://github.com/erenertemden/poleposition",
          label: "GitHub",
          position: "right",
        },
      ],
    },
    footer: {
      style: "dark",
      links: [
        {
          title: "Docs",
          items: [
            {label: "Getting Started", to: "/getting-started"},
            {label: "CLI Reference", to: "/cli"},
            {label: "Project Checks", to: "/project-checks"},
          ],
        },
        {
          title: "Project",
          items: [
            {
              label: "GitHub",
              href: "https://github.com/erenertemden/poleposition",
            },
            {
              label: "PyPI",
              href: "https://pypi.org/project/poleposition/",
            },
          ],
        },
      ],
      copyright: `Copyright © ${new Date().getFullYear()} PolePosition.`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
    },
  },
};

module.exports = config;

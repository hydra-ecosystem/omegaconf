import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import CodeBlock from '@theme/CodeBlock';

const example = `from omegaconf import OmegaConf

base = OmegaConf.create({"port": 80})
config = OmegaConf.merge(
    base, {"port": 8080}
)
print(config.port)  # 8080`;

const paths = [
  {
    title: 'Work with configs',
    description: 'Create, change, combine, and exchange configuration data.',
    to: '/docs/concepts/configs-and-values',
  },
  {
    title: 'Derive values',
    description: 'Reference other values and call resolvers when a config is read.',
    to: '/docs/concepts/interpolation',
  },
  {
    title: 'Define a schema',
    description: 'Use dataclasses to validate typed configuration data.',
    to: '/docs/concepts/structured-configs',
  },
];

export default function Home() {
  return (
    <Layout title="Python configuration" description="OmegaConf documentation">
      <main>
        <section className="home-hero">
          <div className="home-shell home-hero__grid">
            <div className="home-hero__copy">
              <h1>OmegaConf</h1>
              <p className="home-hero__lead">
                Flexible configuration for Python. Create configs from Python
                or YAML, merge sources, and validate values with structured
                schemas.
              </p>
              <div className="home-actions">
                <Link className="home-button home-button--primary" to="/docs/get-started/first-config">
                  Get started <span aria-hidden="true">→</span>
                </Link>
                <Link className="home-button home-button--quiet" to="/docs/reference/python-api">
                  Browse the API
                </Link>
              </div>
              <p className="home-release">
                Documentation for stable 2.3 · <Link to="/docs/next/">2.4 prerelease</Link>
              </p>
            </div>
            <div className="home-example" aria-label="OmegaConf example">
              <div className="home-example__bar">
                <span className="home-example__filename">config.py</span>
                <span className="home-example__language">Python</span>
              </div>
              <CodeBlock language="python">{example}</CodeBlock>
              <div className="home-example__output">
                <span>Output</span>
                <strong>8080</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="home-shell home-paths" aria-labelledby="choose-a-path">
          <div className="home-section-heading">
            <h2 id="choose-a-path">Explore the documentation</h2>
          </div>
          <div className="home-paths__grid">
            {paths.map((path) => (
              <Link className="home-path" key={path.title} to={path.to}>
                <h3>{path.title}</h3>
                <p>{path.description}</p>
                <span className="home-path__action" aria-hidden="true">→</span>
              </Link>
            ))}
          </div>
        </section>
      </main>
    </Layout>
  );
}

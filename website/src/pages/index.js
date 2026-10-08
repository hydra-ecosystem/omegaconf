import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
import CodeBlock from '@theme/CodeBlock';
import ThemedImage from '@theme/ThemedImage';
import useBaseUrl from '@docusaurus/useBaseUrl';

const example = `from omegaconf import OmegaConf

base = OmegaConf.create({
    "host": "localhost",
    "port": 80,
    "url": "http://\${host}:\${port}",
})
override = OmegaConf.create({
    "port": 8080,
})
config = OmegaConf.merge(base, override)
print(config.url)`;

const paths = [
  {
    title: 'Work with configs',
    description: 'Create, access, update, merge, and serialize configs.',
    to: '/docs/concepts/configs-and-values',
  },
  {
    title: 'Interpolation and resolvers',
    description: 'Reference config values with interpolation and compute values with resolvers.',
    to: '/docs/concepts/interpolation',
  },
  {
    title: 'Structured configs',
    description: 'Declare typed configs with dataclasses or attrs classes.',
    to: '/docs/concepts/structured-configs',
  },
];

export default function Home() {
  const mascotLight = useBaseUrl('/img/omegaconf-mark.svg');
  const mascotDark = useBaseUrl('/img/omegaconf-mark-dark.svg');

  return (
    <Layout title="Python configuration" description="OmegaConf documentation">
      <main>
        <section className="home-hero">
          <div className="home-shell home-hero__grid">
            <div className="home-hero__copy">
              <div className="home-hero__mascot">
                <ThemedImage
                  alt="Fingi, the OmegaConf mascot"
                  title="Fingi"
                  sources={{light: mascotLight, dark: mascotDark}}
                  width={220}
                  height={220}
                />
              </div>
              <h1>OmegaConf</h1>
              <p className="home-hero__lead">
                Flexible configuration for Python. Create configs from Python
                or YAML, merge configuration sources, use interpolation and
                resolvers, and validate values with structured configs.
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
                Documentation for stable 2.4 · <Link to="/docs/2.3/">2.3 documentation</Link>
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
                <strong>http://localhost:8080</strong>
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

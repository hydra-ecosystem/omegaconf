import React from 'react';
import Head from '@docusaurus/Head';
import {Redirect} from '@docusaurus/router';
import useBaseUrl from '@docusaurus/useBaseUrl';

export default function TupleMigrationRedirect() {
  const destination = useBaseUrl(
    '/docs/migration/2.4#tuple-inputs-no-longer-become-mutable-lists',
  );

  return (
    <>
      <Head>
        <meta httpEquiv="refresh" content={`0;url=${destination}`} />
      </Head>
      <Redirect to={destination} />
    </>
  );
}

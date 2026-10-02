module.exports = {
  docsSidebar: [
    'intro',
    {type: 'category', label: 'Start', items: ['get-started/install', 'get-started/first-config']},
    {type: 'category', label: 'Work with configs', items: ['concepts/configs-and-values', 'concepts/missing-values', 'guides/merge', 'guides/load-and-save', 'guides/command-line', 'guides/flags', 'guides/debugging']},
    {type: 'category', label: 'Interpolation and resolvers', items: ['concepts/interpolation', 'concepts/resolvers', 'reference/built-in-resolvers', 'guides/custom-resolvers']},
    {type: 'category', label: 'Structured configs', items: ['concepts/structured-configs', 'concepts/field-types', 'concepts/optional-fields', 'guides/schema-validation']},
    {type: 'category', label: 'Reference', items: ['reference/python-api', 'reference/python-api/omegaconf', 'reference/operations', 'reference/types', 'reference/conversion', 'reference/grammar', 'reference/yaml-alias-limits']},
    {type: 'category', label: 'Upgrade', items: ['migration/2.4']},
  ],
};

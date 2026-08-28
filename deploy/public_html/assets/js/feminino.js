(() => {
  'use strict';

  const supportedUtmParameters = [
    'utm_source',
    'utm_medium',
    'utm_campaign',
    'utm_content',
    'utm_term',
  ];
  const currentParameters = new URLSearchParams(window.location.search);
  const preservedParameters = new URLSearchParams();

  supportedUtmParameters.forEach((parameter) => {
    currentParameters.getAll(parameter).forEach((value) => {
      preservedParameters.append(parameter, value);
    });
  });

  const queryString = preservedParameters.toString();
  if (!queryString) {
    return;
  }

  document.querySelectorAll('.js-whatsapp-cta').forEach((cta) => {
    cta.setAttribute('href', `/go/whatsapp/feminino?${queryString}`);
  });
})();

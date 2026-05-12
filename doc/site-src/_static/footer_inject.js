document.addEventListener('DOMContentLoaded', function () {
  try {
    var script = document.currentScript;
    var staticRoot = '_static/';
    if (script && script.src) {
      staticRoot = script.src.replace(/footer_inject\.js(?:\?.*)?$/, '');
    }

    var target = document.querySelector('footer div[role="contentinfo"]');
    if (!target) {
      // fallback to appending to body
      target = document.body;
    }

    // create container and logos
    var container = document.createElement('div');
    container.className = 'eu-footer';
    var logos = document.createElement('div');
    logos.className = 'eu-logos';

    var img1 = document.createElement('img');
    img1.alt = 'Funded by the EU';
    img1.src = staticRoot + 'EN-Funded by the EU-POS.jpg';

    var img2 = document.createElement('img');
    img2.alt = 'EuroHPC JU';
    img2.src = staticRoot + 'EuroHPC JU logo SVG.svg';

    logos.appendChild(img1);
    logos.appendChild(img2);
    container.appendChild(logos);

    // replace existing copyright paragraph if present
    var copyPara = target.querySelector('p');
    if (copyPara) {
      copyPara.parentNode.replaceChild(container, copyPara);
    } else {
      target.appendChild(container);
    }
  } catch (e) {
    console.error('Footer injection failed', e);
  }
});

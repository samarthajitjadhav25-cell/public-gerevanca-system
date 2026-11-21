document.addEventListener('DOMContentLoaded', () => {
  const toggle = document.querySelector('.nav-toggle');
  const nav = document.querySelector('.main-nav');
  if (toggle && nav) toggle.addEventListener('click', () => {
    const isOpen = nav.classList.toggle('open');
    toggle.setAttribute('aria-expanded', String(isOpen));
  });

  document.querySelectorAll('.dismiss').forEach(button => button.addEventListener('click', () => button.closest('.flash')?.remove()));

  document.querySelectorAll('[data-password-toggle]').forEach(button => button.addEventListener('click', () => {
    const input = button.closest('.password-control')?.querySelector('input');
    if (!input) return;
    input.type = input.type === 'password' ? 'text' : 'password';
    button.textContent = input.type === 'password' ? 'Show' : 'Hide';
  }));

  const registration = document.querySelector('[data-register-form]');
  if (registration) registration.addEventListener('submit', event => {
    const password = registration.elements.password;
    const confirmation = registration.elements.confirm_password;
    const message = registration.querySelector('[data-password-error]');
    if (password.value !== confirmation.value) {
      event.preventDefault();
      message.textContent = 'Your passwords do not match.';
      confirmation.setAttribute('aria-invalid', 'true');
      confirmation.focus();
      return;
    }
    message.textContent = '';
  });

  const imageInput = document.querySelector('[data-image-input]');
  const preview = document.querySelector('[data-image-preview]');
  const dropZone = document.querySelector('[data-drop-zone]');
  const previewFile = file => {
    if (!file || !preview) return;
    if (!['image/png', 'image/jpeg', 'image/webp'].includes(file.type)) {
      alert('Choose a PNG, JPG, JPEG, or WEBP image.');
      if (imageInput) imageInput.value = '';
      preview.style.display = 'none';
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      alert('Please choose an image smaller than 5 MB.');
      if (imageInput) imageInput.value = '';
      preview.style.display = 'none';
      return;
    }
    preview.src = URL.createObjectURL(file);
    preview.style.display = 'block';
  };
  imageInput?.addEventListener('change', () => previewFile(imageInput.files[0]));
  if (dropZone && imageInput) {
    ['dragenter', 'dragover'].forEach(type => dropZone.addEventListener(type, event => {
      event.preventDefault(); dropZone.classList.add('dragover');
    }));
    ['dragleave', 'drop'].forEach(type => dropZone.addEventListener(type, event => {
      event.preventDefault(); dropZone.classList.remove('dragover');
    }));
    dropZone.addEventListener('drop', event => {
      const file = event.dataTransfer.files[0];
      if (!file) return;
      const transfer = new DataTransfer(); transfer.items.add(file); imageInput.files = transfer.files; previewFile(file);
    });
  }

  const search = document.querySelector('[data-complaint-search]');
  const category = document.querySelector('[data-category-filter]');
  const status = document.querySelector('[data-status-filter]');
  const rows = [...document.querySelectorAll('[data-complaint-row]')];
  const empty = document.querySelector('[data-filter-empty]');
  const filterRows = () => {
    const query = search?.value.trim().toLowerCase() || '';
    let shown = 0;
    rows.forEach(row => {
      const matches = row.dataset.search.includes(query)
        && (!category?.value || row.dataset.category === category.value)
        && (!status?.value || row.dataset.status === status.value);
      row.hidden = !matches;
      if (matches) shown++;
    });
    if (empty) empty.style.display = shown ? 'none' : 'block';
  };
  [search, category, status].forEach(control => control?.addEventListener('input', filterRows));

  document.querySelectorAll('form.form-stack, form.filter-bar').forEach(form => form.addEventListener('submit', () => {
    const submit = form.querySelector('button[type="submit"], button:not([type])');
    if (submit && form.checkValidity()) {
      submit.disabled = true;
      submit.dataset.originalText = submit.textContent;
      submit.textContent = 'Please wait…';
    }
  }));
});

document.addEventListener("DOMContentLoaded", () => {
  // Мобильное бургер-меню
  const burgerBtn = document.getElementById("burgerBtn");
  const mainNav = document.getElementById("mainNav");

  if (burgerBtn && mainNav) {
    burgerBtn.addEventListener("click", () => {
      const isOpen = mainNav.classList.toggle("is-open");
      burgerBtn.classList.toggle("is-open", isOpen);
      burgerBtn.setAttribute("aria-expanded", isOpen);
    });

    // На мобильном тап по пункту меню раскрывает подкатегории
    document.querySelectorAll(".nav-item > a").forEach((link) => {
      link.addEventListener("click", (e) => {
        if (window.innerWidth <= 720) {
          e.preventDefault();
          link.parentElement.classList.toggle("is-open");
        }
      });
    });
  }

  // Поиск
  const searchToggle = document.getElementById("searchToggle");
  const searchPanel = document.getElementById("searchPanel");

  if (searchToggle && searchPanel) {
    searchToggle.addEventListener("click", () => {
      const isOpen = searchPanel.classList.toggle("is-open");
      if (isOpen) {
        searchPanel.querySelector("input").focus();
      }
    });
  }

  // Вкладки витрины товаров (Хиты / Новинки / Скидки)
  const tabs = document.querySelectorAll(".tab");
  const panels = document.querySelectorAll(".product-slider");

  tabs.forEach((tab) => {
    tab.addEventListener("click", () => {
      const target = tab.dataset.tab;

      tabs.forEach((t) => {
        t.classList.toggle("is-active", t === tab);
        t.setAttribute("aria-selected", t === tab);
      });

      panels.forEach((panel) => {
        panel.classList.toggle("is-active", panel.dataset.panel === target);
      });
    });
  });

  // Стрелки слайдера товаров — прокручивают активную вкладку
  document.querySelectorAll(".slider-arrow").forEach((btn) => {
    btn.addEventListener("click", () => {
      const wrap = btn.closest(".product-slider-wrap");
      const active = wrap && wrap.querySelector(".product-slider.is-active");
      if (!active) return;
      const dir = btn.classList.contains("slider-arrow--prev") ? -1 : 1;
      active.scrollBy({
        left: dir * active.clientWidth * 0.9,
        behavior: "smooth",
      });
    });
  });

  // Плитки категорій на головній: по черзі показуємо кожну «великою»,
  // щоб товар/фото було добре видно не тільки в першій категорії.
  // Працює однаково і на десктопі, і на мобільному — за розкладку
  // відповідає CSS (медіа-запити), тут лише міняються класи й order.
  const categoriesGrid = document.querySelector(".categories__grid");
  if (categoriesGrid) {
    const tiles = Array.from(categoriesGrid.querySelectorAll(".cat-tile"));
    const prefersReducedMotion = window.matchMedia(
      "(prefers-reduced-motion: reduce)"
    ).matches;

    if (tiles.length > 1 && !prefersReducedMotion) {
      let activeIndex = tiles.findIndex((t) =>
        t.classList.contains("cat-tile--large")
      );
      if (activeIndex === -1) activeIndex = 0;

      const applyLayout = (index) => {
        let order = 1;
        tiles.forEach((tile, i) => {
          const isLarge = i === index;
          tile.classList.toggle("cat-tile--large", isLarge);
          tile.classList.toggle("cat-tile--small", !isLarge);
          tile.style.order = isLarge ? "0" : String(order++);
        });
      };

      applyLayout(activeIndex);

      const ROTATE_MS = 4500;
      const FADE_MS = 220;
      let timer = null;

      const rotate = () => {
        categoriesGrid.classList.add("is-rotating");
        window.setTimeout(() => {
          activeIndex = (activeIndex + 1) % tiles.length;
          applyLayout(activeIndex);
          categoriesGrid.classList.remove("is-rotating");
        }, FADE_MS);
      };

      const start = () => {
        if (timer) return;
        timer = window.setInterval(rotate, ROTATE_MS);
      };
      const stop = () => {
        window.clearInterval(timer);
        timer = null;
      };

      start();
      // На паузі під час наведення/фокусу — щоб не «стрибало» під курсором
      categoriesGrid.addEventListener("mouseenter", stop);
      categoriesGrid.addEventListener("mouseleave", start);
      categoriesGrid.addEventListener("focusin", stop);
      categoriesGrid.addEventListener("focusout", start);
    }
  }
});

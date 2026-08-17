document.addEventListener("DOMContentLoaded", () => {
  // Шапка завжди position: fixed (див. CSS) — а її «top» щокадрово
  // підлаштовується під скрол, тому вона плавно виїжджає з-під topbar
  // і лишається зверху, без різких стрибків чи зникнення (був баг із
  // position: sticky, а потім — різкий стрибок при перемиканні класу).
  // Spacer резервує сталу висоту шапки один раз і більше не змінюється.
  const topbarEl = document.querySelector(".topbar");
  const headerEl = document.querySelector(".header");
  const headerSpacer = document.getElementById("headerSpacer");

  if (headerEl) {
    let topbarHeight = topbarEl ? topbarEl.offsetHeight : 0;

    const measure = () => {
      topbarHeight = topbarEl ? topbarEl.offsetHeight : 0;
      if (headerSpacer)
        headerSpacer.style.height = headerEl.offsetHeight + "px";
    };

    const update = () => {
      const offset = Math.max(0, topbarHeight - window.scrollY);
      headerEl.style.top = offset + "px";
    };

    let ticking = false;
    window.addEventListener(
      "scroll",
      () => {
        if (!ticking) {
          window.requestAnimationFrame(() => {
            update();
            ticking = false;
          });
          ticking = true;
        }
      },
      { passive: true }
    );

    window.addEventListener("resize", () => {
      measure();
      update();
    });
    window.addEventListener("load", () => {
      measure();
      update();
    });

    measure();
    update();
  }

  // Мобильное бургер-меню
  const burgerBtn = document.getElementById("burgerBtn");
  const mainNav = document.getElementById("mainNav");
  const navCloseBtn = document.getElementById("navCloseBtn");
  const navBackdrop = document.getElementById("navBackdrop");

  if (burgerBtn && mainNav) {
    const setNavOpen = (isOpen) => {
      mainNav.classList.toggle("is-open", isOpen);
      burgerBtn.classList.toggle("is-open", isOpen);
      burgerBtn.setAttribute("aria-expanded", isOpen);
      if (navBackdrop) navBackdrop.classList.toggle("is-open", isOpen);
    };

    burgerBtn.addEventListener("click", () => {
      setNavOpen(!mainNav.classList.contains("is-open"));
    });

    // Крестик усередині меню — закриває його
    if (navCloseBtn) {
      navCloseBtn.addEventListener("click", () => setNavOpen(false));
    }

    // Клік мимо меню (по затемненому фону) — теж закриває
    if (navBackdrop) {
      navBackdrop.addEventListener("click", () => setNavOpen(false));
    }

    // Esc — закриває меню
    document.addEventListener("keydown", (e) => {
      if (e.key === "Escape" && mainNav.classList.contains("is-open")) {
        setNavOpen(false);
      }
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

  // Каталог: кнопка «Завантажити ще» (+ автопідвантаження, коли кнопка
  // з'являється у зоні видимості — ефект нескінченного скролу)
  const loadMoreBtn = document.getElementById("loadMoreBtn");
  const catalogGrid = document.querySelector(".catalog__grid");

  if (loadMoreBtn && catalogGrid) {
    let nextPage = parseInt(loadMoreBtn.dataset.nextPage, 10) || 2;
    let isLoading = false;
    const path = loadMoreBtn.dataset.path || window.location.pathname;
    const baseQuery = loadMoreBtn.dataset.query || "";

    const loadMore = () => {
      if (isLoading) return;
      isLoading = true;
      loadMoreBtn.disabled = true;
      loadMoreBtn.textContent = "Завантаження…";

      const qs = baseQuery
        ? `${baseQuery}&page=${nextPage}`
        : `page=${nextPage}`;

      fetch(`${path}?${qs}`, { headers: { "X-Requested-With": "fetch" } })
        .then((res) => {
          const hasMore = res.headers.get("X-Has-More") === "1";
          return res.text().then((html) => ({ html, hasMore }));
        })
        .then(({ html, hasMore }) => {
          catalogGrid.insertAdjacentHTML("beforeend", html);
          nextPage += 1;
          isLoading = false;
          if (hasMore) {
            loadMoreBtn.disabled = false;
            loadMoreBtn.textContent = "Завантажити ще";
          } else {
            loadMoreBtn.remove();
          }
        })
        .catch(() => {
          isLoading = false;
          loadMoreBtn.disabled = false;
          loadMoreBtn.textContent = "Завантажити ще";
        });
    };

    loadMoreBtn.addEventListener("click", loadMore);

    if ("IntersectionObserver" in window) {
      const observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) loadMore();
          });
        },
        { rootMargin: "600px" }
      );
      observer.observe(loadMoreBtn);
    }
  }
});

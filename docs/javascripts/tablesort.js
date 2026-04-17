// Initialise tablesort on every <table class="sortable"> after each page load.
// `document$` is the Material-for-MkDocs observable that fires on both the
// initial load and the SPA-style instant-navigation page swaps, so this runs
// exactly once per rendered page. The Tablesort global is provided by the
// vendored tablesort.min.js loaded immediately before this script.
document$.subscribe(function () {
  document.querySelectorAll("table.sortable").forEach(function (table) {
    if (!table.dataset.tablesort) {
      new Tablesort(table);
      table.dataset.tablesort = "1";
    }
  });
});

import TabMenu from './data';
Component({
  data: {
    active: 0,
    list: TabMenu,
  },

  methods: {
    onTabClick(event) {
      const index = event.currentTarget.dataset.index;
      if (index === this.data.active) return;
      this.setData({ active: index });
      wx.switchTab({
        url: this.data.list[index].url.startsWith('/')
          ? this.data.list[index].url
          : `/${this.data.list[index].url}`,
      });
    },

    init() {
      const page = getCurrentPages().pop();
      const route = page ? page.route.split('?')[0] : '';
      const active = this.data.list.findIndex(
        (item) =>
          (item.url.startsWith('/') ? item.url.substr(1) : item.url) ===
          `${route}`,
      );
      this.setData({ active });
    },
  },
});
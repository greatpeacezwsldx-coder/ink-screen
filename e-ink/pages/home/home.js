import { fetchHome } from '../../services/home/home';
import { fetchGoodsList } from '../../services/good/fetchGoods';
import Toast from 'tdesign-miniprogram/toast/index';

const OTHER_BEST_PHOTO_BASE_URL = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/bestphotobefore/';
const ALL_PHOTO_BASE_URL = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/small/';

const OTHER_BEST_PHOTOS = [
  '0103.jpg',
  '0205.JPG',
  '0406.jpg',
  '0506.jpg',
  '0509.jpg',
  '0615.jpg',
  '0616.jpg',
  '0627.JPG',
  '0628.jpg',
  '0629.jpg',
  '0701.jpg',
  '0706.jpg',
  '0724.jpg',
  '0725.jpg',
  '0805.jpg',
  '0808.jpg',
  '0812.jpg',
  '0926.jpg',
  '1006.jpg',
  '1017.JPG',
  '1031.JPG',
].map(name => ({
  url: OTHER_BEST_PHOTO_BASE_URL + name,
  name: name.replace('.jpg', ''),
}));

const ALL_PHOTO_NAME_TXT_URL = 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/small/name.txt';

Page({
  data: {
    imgSrcs: [],
    tabList: [],
    goodsList: [],
    goodsListLoadStatus: 0,
    pageLoading: false,
    current: 1,
    autoplay: true,
    duration: 500,
    interval: 5000,
    navigation: { type: 'dots' },
    swiperImageProps: { mode: 'aspectFit' },
    tabIndex: 0,
    bestPhoto: {
      url: 'https://mypublicbucket0101.obs.cn-north-4.myhuaweicloud.com/best-photo/%E7%85%A7%E7%89%87%20%2873%29.jpg',
      caption: '一位年轻女性抱着一只白色毛茸茸的小狗，眯眼微笑，背景是室内沙发和竖条纹墙面。',
      memory_score: 85,
      beauty_score: 80,
      reason: '人物与宠物互动温馨，构图自然，光线柔和，情绪表达生动。',
      side_caption: '阳光洒落，与毛茸茸的你共享温柔时光。',
      type: '人物, 宠物',
      exif_make: '',
      exif_model: '',
      exif_datetime: '',
    },
    otherBestPhotos: [],
    allPhotos: [],
    todayPhotos: [],
  },

  goodListPagination: {
    index: 0,
    num: 20,
  },

  onShow() {
    this.getTabBar().init();
  },

  onLoad() {
    this.init();
  },

  onReachBottom() {
    if (this.data.goodsListLoadStatus === 0) {
      this.loadGoodsList();
    }
  },

  onPullDownRefresh() {
    this.init();
  },

  init() {
    this.loadHomePage();
    this.loadOtherBestPhotos();
    this.loadAllPhotos();
  },

  loadOtherBestPhotos() {
    this.setData({ otherBestPhotos: OTHER_BEST_PHOTOS });
  },

  loadAllPhotos() {
    wx.request({
      url: ALL_PHOTO_NAME_TXT_URL,
      success: (res) => {
        if (res.statusCode === 200 && res.data) {
          const fileNames = res.data.trim().split('\n').filter(name => name.trim());
          const photos = fileNames.map(name => {
            const trimmedName = name.trim();
            return {
              url: ALL_PHOTO_BASE_URL + encodeURIComponent(trimmedName),
              name: trimmedName.replace(/\.(jpg|jpeg|png|gif|bmp)$/i, ''),
            };
          });
          this.setData({ allPhotos: photos });
          this.filterTodayPhotos(photos);
        }
      },
      fail: (err) => {
        console.error('加载全部照片列表失败:', err);
      },
    });
  },

  filterTodayPhotos(photos) {
    const today = new Date();
    const targetMonth = today.getMonth() + 1;
    const targetDay = today.getDate();
    const targetMonthStr = targetMonth.toString().padStart(2, '0');
    const targetDayStr = targetDay.toString().padStart(2, '0');
    const targetDatePattern = `${targetMonthStr}${targetDayStr}`;

    const todayPhotos = photos.filter(photo => {
      const fileName = photo.name;
      const match1 = fileName.match(/^(\d{2})\.(\d{2})\.(\d{2})/);
      const match2 = fileName.match(/^(\d{4})\.(\d{2})\.(\d{2})/);
      const match3 = fileName.match(/^(\d{4})/);

      if (match1) {
        const month = parseInt(match1[1], 10);
        const day = parseInt(match1[2], 10);
        return month === targetMonth && day === targetDay;
      } else if (match2) {
        const month = parseInt(match2[2], 10);
        const day = parseInt(match2[3], 10);
        return month === targetMonth && day === targetDay;
      } else if (match3) {
        const dateStr = match3[1];
        if (dateStr.length === 8) {
          const month = parseInt(dateStr.substring(4, 6), 10);
          const day = parseInt(dateStr.substring(6, 8), 10);
          return month === targetMonth && day === targetDay;
        }
      }

      if (fileName.startsWith(targetDatePattern)) {
        return true;
      }

      return false;
    });

    this.setData({ todayPhotos });
  },

  loadHomePage() {
    wx.stopPullDownRefresh();

    this.setData({
      pageLoading: true,
    });
    fetchHome().then(({ swiper, tabList }) => {
      this.setData({
        tabList,
        imgSrcs: swiper,
        pageLoading: false,
      });

      if (swiper && swiper.length > 0) {
        this.calculateSwiperHeight(swiper[0]);
      }
    });
  },

  calculateSwiperHeight(imgUrl) {
    wx.getImageInfo({
      src: imgUrl,
      success: (res) => {
        const screenWidth = wx.getSystemInfoSync().windowWidth;
        const scale = res.height / res.width;
        const swiperHeight = screenWidth * scale;
        this.setData({
          swiperHeight: swiperHeight,
        });
      },
      fail: () => {
        this.setData({
          swiperHeight: 400,
        });
      },
    });
  },

  tabChangeHandle(e) {
    this.setData({ tabIndex: e.detail });
  },

  onTabClick(e) {
    const key = parseInt(e.currentTarget.dataset.key, 10);
    this.setData({ tabIndex: key });
  },

  onReTry() {
    this.loadGoodsList();
  },

  async loadGoodsList(fresh = false) {
    if (fresh) {
      wx.pageScrollTo({
        scrollTop: 0,
      });
    }

    this.setData({ goodsListLoadStatus: 1 });

    const pageSize = this.goodListPagination.num;
    let pageIndex = this.data.tabIndex * pageSize + this.goodListPagination.index + 1;
    if (fresh) {
      pageIndex = 0;
    }

    try {
      const nextList = await fetchGoodsList(pageIndex, pageSize);
      this.setData({
        goodsList: fresh ? nextList : this.data.goodsList.concat(nextList),
        goodsListLoadStatus: 0,
      });

      this.goodListPagination.index = pageIndex;
      this.goodListPagination.num = pageSize;
    } catch (err) {
      this.setData({ goodsListLoadStatus: 3 });
    }
  },

  goodListClickHandle(e) {
    const { index } = e.detail;
    const { spuId } = this.data.goodsList[index];
    wx.navigateTo({
      url: `/pages/goods/details/index?spuId=${spuId}`,
    });
  },

  goodListAddCartHandle() {
    Toast({
      context: this,
      selector: '#t-toast',
      message: '点击加入购物车',
    });
  },

  navToSearchPage() {
    wx.navigateTo({ url: '/pages/goods/search/index' });
  },

  navToActivityDetail({ detail }) {
    const { index: promotionID = 0 } = detail || {};
    wx.navigateTo({
      url: `/pages/promotion/promotion-detail/index?promotion_id=${promotionID}`,
    });
  },
});

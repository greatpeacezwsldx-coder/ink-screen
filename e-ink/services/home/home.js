import { config, cdnBase } from '../../config/index';

/** 获取首页数据 */
function mockFetchHome() {
  const { delay } = require('../_utils/delay');
  const { fetchSwiperImages } = require('../../model/swiper');
  return delay().then(() => {
    return new Promise((resolve) => {
      fetchSwiperImages((images) => {
        resolve({
          swiper: images,
          tabList: [
            {
              text: '今日最佳',
              key: 0,
            },
            {
              text: '往年今日',
              key: 1,
            },
            {
              text: '全部照片',
              key: 2,
            },
            {
              text: '他日最佳',
              key: 3,
            },
          ],
          activityImg: `${cdnBase}/activity/banner.png`,
        });
      });
    });
  });
}

/** 获取首页数据 */
export function fetchHome() {
  if (config.useMock) {
    return mockFetchHome();
  }
  return new Promise((resolve) => {
    resolve('real api');
  });
}
